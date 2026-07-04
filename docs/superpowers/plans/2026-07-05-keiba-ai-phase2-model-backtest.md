# 競馬予想AI Phase 2（モデル＋回収率backtest）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Phase 1 で集めた `race.db` から、各馬の勝率(1着)・3着内確率を LightGBM で学習し、単勝・ワイドの「期待値プラス馬券」を時系列backtestして回収率を算出する。GO/NO-GO判断（回収率>100%か）を出す。

**Architecture:** features(リーク防止の学習テーブル生成) → model(2つのLightGBM: 勝率/3着内) → betting(Harvilleワイド同時確率＋EV計算) → backtest(時系列holdout・回収率レポート)。各モジュールは独立・TDD。実データが溜まる前でも合成データ＋部分データでドライラン可能。

**Tech Stack:** Python 3.9+, pandas, numpy, lightgbm, scikit-learn, sqlite3, pytest。

## Global Constraints

- **データリーク厳禁**: すべての集計特徴量は「そのレース発走時点で知り得る情報」のみ。未来の着順・オッズ・払戻を特徴量に入れない。
- **オッズ(win_odds)・人気(popularity)は特徴量に入れない**（市場追従を防ぐ）。EV計算でのみ使用。
- **時系列分割**: 学習期間と検証期間は日付で分け、未来データで学習しない。
- 単勝・ワイドのみ対象。3連系は扱わない。
- 非完走馬(finish_pos NULL)は「1着でない/3着内でない」負例として扱う（除外しない）。
- ワイドのbacktestは payouts テーブルの実払戻で答え合わせ。
- 作業ディレクトリ: `競馬予想アプリ/`。既存 `keiba/` に追加。テストは `tests/`。
- TDD、タスクごとコミット、タスク固有ファイルのみ add。

## File Structure

```
競馬予想アプリ/keiba/
  features.py    # race.db -> 学習用DataFrame（リーク防止）
  model.py       # 2モデル学習・保存・推論、レース内正規化
  betting.py     # Harvilleワイド同時確率、単勝/ワイドEV、買い目選定
  backtest.py    # 時系列holdout、回収率レポート
競馬予想アプリ/scripts/
  train.py         # 学習実行CLI
  backtest_run.py  # backtest実行→レポートCLI
競馬予想アプリ/tests/
  test_features.py test_model.py test_betting.py test_backtest.py
```

---

### Task 1: 特徴量生成（features.py）— リーク防止が最重要

**Files:** Create `keiba/features.py`; Test `tests/test_features.py`

**Interfaces / Produces:**
- `features.build_dataset(conn) -> pandas.DataFrame` : 1行=1レース1頭。列: race_id, date, horse_id, horse_no, 特徴量各種, `y_win`(finish_pos==1→1), `y_top3`(1<=finish_pos<=3→1), `win_odds`(EV用に保持・特徴量ではない)。
- 特徴量(発走時点のみ): distance, surface, going, race_class, field_size, draw, sex, age, weight_carried, days_since_last(前走間隔), horse_prev_finish, horse_avg_finish3, horse_avg_last3f, jockey_win_rate(当該レース日より前), trainer_win_rate(同), horse_runs(過去出走数)。集計系は**当該レースの date より前のレコードのみ**で算出。sex/age は sex_age から分解。

- [ ] Step1: 失敗テスト（合成の小さな races/entries を in-memory DB に入れ、①y_winが着順1の馬だけ1、②jockey_win_rateが未来レースを含まない、③非完走馬(finish_pos NULL)はy_win=0/y_top3=0 を検証）
- [ ] Step2: 失敗確認 `python3 -m pytest tests/test_features.py -v`
- [ ] Step3: features.py 実装（races×entriesをdate昇順JOIN、horse/jockey/trainerごとに「その行のdateより前」の統計。カテゴリはpandas category、NaNは明示埋め）
- [ ] Step4: 成功確認
- [ ] Step5: 部分データでドライラン（行数・NaN比率・ラベル率を確認）
- [ ] Step6: commit `feat(keiba): leakage-safe feature engineering`

**リーク検知テスト(必須)**: あるレースの jockey_win_rate がそのレース以降の結果を含まないことを、時系列合成データで明示 assert。

---

### Task 2: モデル学習（model.py）

**Files:** Create `keiba/model.py`, `scripts/train.py`; Test `tests/test_model.py`

**Interfaces / Produces:**
- `model.time_split(df, valid_frac=0.2) -> (train_df, valid_df)` : dateで時系列分割（後ろvalid_fracを検証）
- `model.train_models(train_df) -> dict` : `{"win": lgbm, "top3": lgbm, "feature_cols":[...], "meta":{trained dates}}`
- `model.predict(models, df) -> DataFrame` : 各行に p_win_raw,p_top3_raw を付与し、**レース内正規化**した p_win(同一race_idで合計=1), p_top3 を追加
- `model.save(models, path)` / `model.load(path)` : メタ(学習期間・バージョン)込み

- [ ] Step1: 失敗テスト（合成データで train_models が2モデル返す、predictが各race_idでp_win合計≈1、time_splitがdate順で重複しない）
- [ ] Step2: 失敗確認
- [ ] Step3: 実装（LightGBM binary、categorical_feature指定、p_win=p_win_raw/race内合計）
- [ ] Step4: 成功確認
- [ ] Step5: `scripts/train.py`（build_dataset→time_split→train→save）。ドライラン `python3 scripts/train.py --db data/race.db --out data/models.pkl`
- [ ] Step6: commit `feat(keiba): train win/top3 LightGBM models with in-race normalization`

---

### Task 3: 期待値・ワイド同時確率（betting.py）

**Files:** Create `keiba/betting.py`; Test `tests/test_betting.py`

**Interfaces / Produces:**
- `betting.wide_pair_prob(p_top3_i, p_top3_j) -> float` : 2頭が共に3着内の近似同時確率（まず独立近似ベースで開始、テストで挙動確認）
- `betting.win_ev(p_win, win_odds) -> float` : `p_win * win_odds`
- `betting.wide_ev(pair_prob, wide_payout_odds) -> float` : `pair_prob * wide_payout_odds`
- `betting.select_win_bets(race_df, threshold) -> DataFrame` : p_win*win_odds>threshold の行
- `betting.select_wide_bets(race_df, wide_odds_lookup, threshold) -> list` : 全2頭組でEV>thresholdのペア

- [ ] Step1: 失敗テスト（既知値で照合。例 p_win=0.25,odds=5.0→EV=1.25>1.0で買い。p_top3両方0.5→pair近似が 0<val<=0.5）
- [ ] Step2: 失敗確認
- [ ] Step3: 実装
- [ ] Step4: 成功確認
- [ ] Step5: commit `feat(keiba): expected-value and wide pair-probability betting logic`

---

### Task 4: 時系列backtest＋回収率レポート（backtest.py）

**Files:** Create `keiba/backtest.py`, `scripts/backtest_run.py`; Test `tests/test_backtest.py`

**Interfaces / Produces:**
- `backtest.run_backtest(conn, *, valid_frac, thresholds) -> dict` : valid期間で学習済みモデル→買い目選定→**実払戻(payouts)で回収率計算**。券種別×EVしきい値別×オッズ帯別の回収率・的中率・購入点数・収支＋キャリブレーション（予測勝率bin vs 実勝率）
- 単勝回収率 = Σ(的中payout)/Σ(100*点数)。ワイドは payouts.wide を combination 照合で参照。
- `backtest.format_report(result) -> str`

- [ ] Step1: 失敗テスト（合成: 既知の勝率/オッズ/払戻で回収率が手計算と一致。学習期間と検証期間が重ならないことをassert）
- [ ] Step2: 失敗確認
- [ ] Step3: 実装
- [ ] Step4: 成功確認
- [ ] Step5: `scripts/backtest_run.py --db data/race.db` → レポート出力。**GO/NO-GO**: いずれかの設定で回収率が安定して100%超か
- [ ] Step6: commit `feat(keiba): time-series backtest and ROI report (GO/NO-GO)`

---

## Self-Review

- スペック§4カバレッジ: 特徴量(Task1)/2モデル+正規化(Task2)/Harvilleワイド+EV(Task3)/時系列backtest+回収率+キャリブレーション(Task4)。オッズ非特徴量化(Task1制約)。リーク防止(Task1検知テスト+Task4時系列assert)。
- 型整合: build_dataset の列名 → model.predict の参照 → betting/backtest の参照が一致（race_id, p_win, p_top3, win_odds, y_win, y_top3）。
- Task2以降は部分データでも動作（データ少時は指標が不安定なだけ）。本番判断は収集完了後に再実行。

## 注意（並行収集との関係）
- 収集ジョブが `data/race.db` に書き込み中。features/train/backtest は**読み取り**なので基本問題ないが、まれに "database is locked" が出たらリトライ。ドライランは部分データでの動作確認が目的。**GO/NO-GO の最終判断は5年収集完了後**に `scripts/backtest_run.py` を再実行して行う。
