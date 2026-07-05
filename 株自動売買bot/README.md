# 株自動売買bot（Alpaca ペーパートレード）

米国株を対象に、5分足のEMAクロス順張り戦略で自動売買する bot。
**ペーパートレード（仮想資金）専用**として設計されています。実資金での運用はスコープ外です。

> ⚠️ 免責: 投資は自己責任です。まずペーパートレードで十分に成績を検証してください。
> 本 bot は学習・検証目的であり、利益を保証するものではありません。

## 構成

| ファイル | 役割 |
|---|---|
| `config.py` | 銘柄リスト・戦略/リスクのパラメータ・認証情報の読み込み |
| `domain.py` | ドメイン型（`Signal`, `Position`） |
| `strategy.py` | バー→売買シグナル（純粋関数・戦略の頭脳） |
| `risk.py` | 発注サイズ・保有数上限・損切り/日次損失の判定 |
| `journal.py` | 売買ログ（CSV）＋損益サマリー |
| `notifier.py` | Slack 通知 |
| `data.py` | Alpaca から5分足を取得 |
| `broker.py` | Alpaca へ発注（ペーパー固定）・保有/口座取得 |
| `backtest.py` | 過去データで戦略を再生し成績を出力 |
| `run_live.py` | 市場時間中に5分ごとに回すメインループ |

## セットアップ

```bash
cd 株自動売買bot
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

### 1. Alpaca ペーパー口座のAPIキー

1. https://app.alpaca.markets/ でアカウント作成（無料）
2. 画面を **Paper Trading** に切り替える
3. 「API Keys」から **Paper** の API Key / Secret を発行

### 2. Slack Incoming Webhook

1. https://api.slack.com/messaging/webhooks の手順で Incoming Webhook を有効化
2. 通知したいチャンネルを選び、発行された Webhook URL をコピー

### 3. .env を作成

```bash
cp .env.example .env
```

`.env` を開き、発行した値を設定：

```
ALPACA_API_KEY=（Paperの API Key）
ALPACA_SECRET_KEY=（Paperの Secret）
SLACK_WEBHOOK_URL=（Slack Webhook URL）
```

`.env` は `.gitignore` 済みでコミットされません。

## バックテスト（戦略の検証）

過去データで戦略の成績を確認してから本番相当に反映します。例：

```python
# backtest_run.py など任意のスクリプト
from datetime import datetime, timezone, timedelta
import os
from data import MarketData
from backtest import run_backtest
from config import StrategyParams

md = MarketData(os.environ["ALPACA_API_KEY"], os.environ["ALPACA_SECRET_KEY"])
end = datetime.now(timezone.utc) - timedelta(minutes=20)
start = end - timedelta(days=30)
bars = md.get_bars(["AAPL"], start, end, minutes=5)["AAPL"]
print(run_backtest(bars, StrategyParams(), min_bars=22))
```

出力: `total_return`（総リターン）, `num_trades`, `win_rate`, `max_drawdown`。

## 本番ループ（ペーパー）の起動

米国市場時間中（日本時間の深夜〜早朝）に起動します。Mac をスリープさせないため
`caffeinate` の併用を推奨：

```bash
# 環境変数を読み込む（.env を使う場合は事前に export するか、direnv 等を利用）
export $(grep -v '^#' .env | xargs)

# スリープ抑止しつつ起動
caffeinate -i ./.venv/bin/python run_live.py
```

- 市場が開いている間のみ5分ごとに判定・発注します
- クローズ15分前に全ポジションを手仕舞い（日をまたぎません）
- 1日の損失が閾値（既定 -5%）に達するとその日の新規売買を停止します
- 売買と損益は `journal_paper.csv` に記録され、Slack にも通知されます

## パラメータの変更

`config.py` の値を書き換えるだけで挙動を調整できます（コード変更不要）：

- `StrategyParams`: `ema_fast`（既定9）, `ema_slow`（既定21）, `stop_loss_pct`（既定0.02）, `take_profit_pct`（既定0.04）
- `RiskParams`: `max_positions`（既定5）, `position_pct`（既定0.10）, `daily_max_loss_pct`（既定0.05）
- `SYMBOLS`: 対象銘柄リスト

戦略ロジック自体を差し替えたい場合は `strategy.py` の `decide_signal` を編集します
（他のモジュールは変更不要）。**変更後は必ずバックテストで成績を確認**してください。

## テスト

```bash
./.venv/bin/pytest -q
```

外部API（Alpaca / Slack）はモック化しているため、APIキーなしで全テストが実行できます。
