# Phase 1 データ収集パイプライン — ローカル実行の引き継ぎ

Task 1〜6（スキャフォールド・DB・取得器・パーサ・発見・収集オーケストレーション）はここまで
オフラインで実装済み・テスト済みです。ここから先はネットワークで実際のnetkeibaに
アクセスする必要があるため、ユーザーのローカル環境で実行してください。

個人の学習目的でのローカル利用を前提にしています（`keiba/config.py` の
`USER_AGENT`、`SLEEP_MIN`/`SLEEP_MAX` で礼儀正しいアクセス間隔を設定済み）。

## 前提

```bash
cd 競馬予想アプリ
pip install -r requirements.txt
```

## 手順

### 1. フィクスチャ取得（実HTMLを1回だけ保存）

`scripts/save_fixture.py` を開き、`RACE_URL` / `LIST_URL` を実在する直近の
JRAレースに書き換えます。

- `RACE_URL`: `https://db.netkeiba.com/race/<race_id>/` 形式のレース結果ページ
- `LIST_URL`: `https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=<YYYYMMDD>` 形式の開催日一覧ページ

書き換えたら実行します。

```bash
python3 scripts/save_fixture.py
```

`keiba.fetcher.fetch` 経由なので、取得前に必ず2〜4秒のスリープが入り、
取得結果は `data/cache/` にキャッシュされます（2回目以降の実行はキャッシュを
再利用するので再アクセスしません）。

成功すると `tests/fixtures/race_result_sample.html` と
`tests/fixtures/race_list_sample.html` が生成されます。

### 2. パーサ／発見ロジックを実HTMLで検証

```bash
python3 -m pytest tests/test_parser.py tests/test_discovery.py -v
```

フィクスチャが存在するようになったので、これまでスキップされていたテストが
実行されます。

**もし失敗したら**（これは想定内の作業です）:

- `keiba/parser.py` の `parse_race_result` 内、出走馬テーブルの列インデックス
  （`tds[0]`〜`tds[11]` など）・CSSセレクタ（`table.race_table_01`、
  `table.pay_table_01`、`.diary_snap_cut` 等）が、実際に保存された
  `tests/fixtures/race_result_sample.html` の列順・クラス名と一致しているか
  確認し、現物に合わせて調整してください。特に:
  - `finish_pos`（着順）, `horse_no`（馬番）, `jockey`（騎手）, `win_odds`（単勝オッズ）
    の列位置がずれやすい箇所です。
  - 払戻テーブルの `bet_type` 判定（`単勝`/`ワイド` の文字列マッチ）も
    実際のラベル表記と合っているか確認してください。
- `keiba/discovery.py` の `parse_race_ids` 内の正規表現
  （`race_id=(\d{12})` / `/race/(\d{12})`）が、実際の
  `tests/fixtures/race_list_sample.html` 内のリンク形式と一致しているか
  確認してください。一致しない場合はリンクの実際の形式を見て正規表現を
  調整してください。

テストが通るまでこのループ（フィクスチャを見る→セレクタ/正規表現を直す→
再テスト）を繰り返すのが、このタスクの本体作業です。

### 3. 小さな範囲でエンドツーエンド疎通確認

```bash
python3 scripts/collect.py --start 2021-12-26 --end 2021-12-26
python3 scripts/db_stats.py
```

`collect.py` は指定期間内の土日（JRA開催想定日）を割り出し、各日の
レース一覧から race_id を発見し、1レースずつ結果ページを取得・パース・
DB保存します。`db_stats.py` で `data/race.db` の件数・日付範囲・
`ingest_progress` の内訳を確認できます。

同じコマンドをもう一度実行すると、既に処理済みの race_id は
`ingest_progress` テーブルにより `skip` されます（再取得なし）。

### 4. 本収集（直近5年、1年ずつ・再開可能）

selectorsの検証が済んだら、`keiba/config.py` の `DATE_START`/`DATE_END`
（デフォルト `2021-01-01`〜`2025-12-31`）を参考に、1年ずつに区切って
実行することを推奨します（途中で中断しても、再実行すれば
`ingest_progress` により続きから再開されます）。

```bash
python3 scripts/collect.py --start 2021-01-01 --end 2021-12-31
python3 scripts/collect.py --start 2022-01-01 --end 2022-12-31
python3 scripts/collect.py --start 2023-01-01 --end 2023-12-31
python3 scripts/collect.py --start 2024-01-01 --end 2024-12-31
python3 scripts/collect.py --start 2025-01-01 --end 2025-12-31
```

各実行後に `python3 scripts/db_stats.py` で進捗を確認してください。

## Known parser gaps to implement during local validation

`tests/test_parser.py` only checks that expected **keys are present** in the
parsed entry dicts — it does NOT check that the values are correct. A green
`test_parser.py` run therefore does **not** mean these fields are accurate;
they must be verified against the real saved fixture HTML during Step 2
above.

- **`draw`（枠番）** — currently hard-coded to `None` in
  `keiba/parser.py::parse_race_result`. It is never extracted from the table.
  You must locate the actual 枠番 column index in
  `tests/fixtures/race_result_sample.html` and read it via `tds[N]`.
- **`popularity`（人気）** — currently hard-coded to `None` in the same
  function. You must locate the real 人気 column index and read it via
  `tds[N]`, the same way `finish_pos`/`horse_no`/etc. are read.
- **`win_odds`（単勝オッズ）** — uses a fragile heuristic: it scans every
  `<td>` in the row for the *first* cell matching the regex `\d+\.\d` and
  takes that as the odds. This can silently grab the wrong column — e.g.
  `last_3f`（上がり3F タイム）also matches `\d+\.\d` and may appear before
  the real odds column in the row, corrupting the value. This MUST be
  replaced with a fixed column index (`tds[N]`) pinned to the confirmed
  単勝オッズ column, exactly as `finish_pos`, `horse_no`, `jockey`, etc.
  already are.

Each of the above is marked with a `# STUB` / fragile-field comment directly
above it in `keiba/parser.py`. Do not treat a passing `test_parser.py` as
confirmation that these three fields are correct — confirm them by eye
against the saved fixture HTML first.

## 礼儀正しさについて

- `keiba/fetcher.py` は取得の都度 2〜4秒のランダムスリープを挟みます。
- 同一URLは `data/cache/` にキャッシュされ、二度と取得しません。
- 5xx応答時は指数バックオフでリトライします。
- 本パイプラインは個人の学習・研究目的のローカル利用を想定しています。
  大量・高頻度アクセスや商用利用は想定していません。
