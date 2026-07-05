# 競馬予想AI Phase 3（次走予測＋予想家ブレンド）Implementation Plan（草案）

> **前提:** Phase 2 の backtest で回収率>100% の見込み（GO判断）が出てから着手する。NO-GO の場合はモデル/特徴量/戦略の改善が先。本計画は「GOになったら即動ける」ための準備。
>
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development。Steps は checkbox 形式。

**Goal:** 今週（任意日付）の出馬表を取得し、学習済みモデルで各馬の勝率・3着内確率を出し、単勝・ワイドの期待値プラス馬券を出力する。さらに指定した予想家（X/YouTube）の今週分コンテンツを Claude で構造化し、モデルの評価とブレンドして最終買い目を出す。

**Architecture:** entrycard(出馬表取得・パース) → predict(学習済みモデルで確率＋EV) → tipster(X/YouTubeコンテンツ→Claude構造化→数値評価) → blend(モデル×予想家の重み付き合成) → 出力(CSV/表)。予想家パートは無くても予測は出せる（任意上乗せ）。

**Tech Stack:** Python, requests/BeautifulSoup(出馬表), 既存 keiba.model/betting, Anthropic API(claude-*, 予想家テキスト構造化), youtube-transcript-api(字幕), pandas。

## Global Constraints

- 出馬表ページは結果ページと構造が異なる（発走前なので着順・確定オッズが無い/暫定）。**発走前に取得できる情報のみ**で特徴量を作る（Phase1のfeaturesと同じ列を、発走前データから再現）。
- モデルは Phase 2 の学習済み models.pkl をロードして使う（再学習しない）。
- 予想家ブレンドは任意。予想家データが取れない/無い場合はモデル単独で出力。
- 予想家コンテンツの構造化は Claude（最新モデル、claude-* 系）で行う。APIキーは環境変数、コードに埋め込まない（[[api-auth-pattern]]）。
- X の過去一括取得はしない。今週分のみ。YouTube は字幕→テキスト。
- 個人利用・ローカル前提。スクレイピングは Phase1 同様の礼儀（スリープ・キャッシュ）。

## File Structure
```
競馬予想アプリ/keiba/
  entrycard.py   # 出馬表(発走前)取得・パース → featuresと同じ列を発走前情報で構築
  predict.py     # models.pkl ロード → 確率 → EV → 買い目
  tipster.py     # X/YouTube取得 + Claude構造化 → 馬番→評価スコア
  blend.py       # モデル評価 × 予想家評価 の重み付き合成
競馬予想アプリ/scripts/
  predict_race.py # 日付/レース指定 → 予想出力(CSV/表)
```

## Tasks（概要・GO後に bite-size 化して確定）

### Task 1: 出馬表取得・パース（entrycard.py）
- 発走前の出馬表ページを取得（race.netkeiba.com の shutuba 等）。Phase1 fetcher を再利用。
- features と同じ特徴量を**発走前に判る情報**で構築（過去成績は race.db から参照、当該レースは未確定）。
- TDD: 保存した出馬表フィクスチャに対してパース検証。

### Task 2: 予測・買い目（predict.py）
- models.pkl ロード → entrycard の特徴量で predict → betting で EV・買い目選定。
- 出力: 馬番・馬名・勝率・単勝オッズ(暫定)・期待値・買い目フラグ。
- TDD: 合成特徴量＋ダミーモデルで確率→EV→選定を検証。

### Task 3: 予想家コンテンツ構造化（tipster.py）
- 入力: X投稿テキスト or YouTube字幕（手動 or 半自動取得）。
- Claude に渡し「馬番→評価スコア(本命度)・推奨券種」の構造化JSONを得る（形式バラバラでも正規化）。
- TDD: 固定サンプルテキスト→期待する構造化出力（Claude呼び出しはモック、パース/正規化ロジックをテスト）。
- APIキーは env、[[api-auth-pattern]] に沿う。

### Task 4: ブレンド（blend.py）
- モデルの p_win/EV と予想家スコアを重み付き合成（重みは Phase2/実績で調整可能なパラメータ）。
- 予想家データ欠如時はモデル単独にフォールバック。
- TDD: 既知入力で合成結果を照合、フォールバック動作を検証。

### Task 5: 出力CLI（scripts/predict_race.py）
- 日付/レース指定 → entrycard→predict→(あれば)tipster→blend→表/CSV出力。

## 注意
- 本計画は Phase 2 GO 後に bite-size 化して確定。予想家パート（X/YouTube）は取得性に不確実性があるため、まず predict.py（モデル単独予測）を先に価値化し、tipster/blend を上乗せする順で進める。
