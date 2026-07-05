# 株式自動売買bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 米国株を Alpaca のペーパートレードで自動売買する bot を作り、5 分足ルールベース戦略・リスク管理・記録・Slack通知・バックテストを備え、ローカル Mac の夜間に自律稼働させる。

**Architecture:** 責務ごとにモジュール分割。`strategy.py` は「バー→シグナル」の純粋関数にし、本番ループ（`run_live.py`）とバックテスト（`backtest.py`）で同じ頭脳を再利用する。外部 IO（Alpaca / Slack）はラッパに閉じ込め、テストではモック化する。

**Tech Stack:** Python 3.9+ / venv, `alpaca-py`, `pandas`, `requests`, `pytest`

## Global Constraints

- 資金は **ペーパートレードのみ**。`broker.py` はデフォルトでペーパー環境（`paper=True`）に固定。実資金発注はスコープ外。
- 認証情報（Alpaca API key/secret, Slack Webhook URL）は **環境変数**から読む。コードやリポジトリにハードコードしない。`.env` は `.gitignore` 対象。
- 空売り禁止（買いのみ）。日をまたがない（クローズ前フラット化）。
- 純粋関数の原則: `strategy.py` と `risk.py` は IO・副作用を持たない。
- プロジェクトルート: `株自動売買bot/`。テストは `株自動売買bot/tests/`。
- 全モジュールで型ヒントを付ける。時刻は tz-aware（US/Eastern）で扱う。

---

### Task 1: プロジェクト初期化と設定

**Files:**
- Create: `株自動売買bot/requirements.txt`
- Create: `株自動売買bot/.gitignore`
- Create: `株自動売買bot/.env.example`
- Create: `株自動売買bot/config.py`
- Create: `株自動売買bot/tests/__init__.py`
- Create: `株自動売買bot/tests/test_config.py`

**Interfaces:**
- Produces:
  - `StrategyParams` dataclass: `ema_fast:int=9, ema_slow:int=21, stop_loss_pct:float=0.02, take_profit_pct:float=0.04`
  - `RiskParams` dataclass: `max_positions:int=5, position_pct:float=0.10, daily_max_loss_pct:float=0.05`
  - `SYMBOLS: list[str]` (初期: `["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","AVGO","JPM"]`)
  - `TIMEFRAME_MINUTES:int=5`, `FLATTEN_BEFORE_CLOSE_MIN:int=15`
  - `load_credentials() -> Credentials` (dataclass: `alpaca_key:str, alpaca_secret:str, slack_webhook:str`), 環境変数 `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`/`SLACK_WEBHOOK_URL` から読む。未設定は `RuntimeError`。

- [ ] **Step 1: venv 作成と依存インストール**

```bash
cd "株自動売買bot" && python3 -m venv .venv && ./.venv/bin/pip install --upgrade pip && ./.venv/bin/pip install alpaca-py pandas requests pytest
```

- [ ] **Step 2: requirements.txt / .gitignore / .env.example を作成**

`requirements.txt`:
```
alpaca-py
pandas
requests
pytest
```

`.gitignore`:
```
.venv/
.env
__pycache__/
*.pyc
journal_*.csv
```

`.env.example`:
```
ALPACA_API_KEY=your_paper_key
ALPACA_SECRET_KEY=your_paper_secret
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_config.py`:
```python
import os
import pytest
import config

def test_strategy_params_defaults():
    p = config.StrategyParams()
    assert p.ema_fast == 9 and p.ema_slow == 21
    assert p.stop_loss_pct == 0.02 and p.take_profit_pct == 0.04

def test_risk_params_defaults():
    r = config.RiskParams()
    assert r.max_positions == 5 and r.position_pct == 0.10
    assert r.daily_max_loss_pct == 0.05

def test_symbols_nonempty():
    assert len(config.SYMBOLS) >= 5

def test_load_credentials_reads_env(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "k")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "u")
    c = config.load_credentials()
    assert c.alpaca_key == "k" and c.alpaca_secret == "s" and c.slack_webhook == "u"

def test_load_credentials_missing_raises(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        config.load_credentials()
```

- [ ] **Step 4: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'config'`)

- [ ] **Step 5: config.py を実装**

```python
from dataclasses import dataclass, field
import os

@dataclass
class StrategyParams:
    ema_fast: int = 9
    ema_slow: int = 21
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04

@dataclass
class RiskParams:
    max_positions: int = 5
    position_pct: float = 0.10
    daily_max_loss_pct: float = 0.05

@dataclass
class Credentials:
    alpaca_key: str
    alpaca_secret: str
    slack_webhook: str

SYMBOLS = ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","AVGO","JPM"]
TIMEFRAME_MINUTES = 5
FLATTEN_BEFORE_CLOSE_MIN = 15

def load_credentials() -> Credentials:
    try:
        return Credentials(
            alpaca_key=os.environ["ALPACA_API_KEY"],
            alpaca_secret=os.environ["ALPACA_SECRET_KEY"],
            slack_webhook=os.environ["SLACK_WEBHOOK_URL"],
        )
    except KeyError as e:
        raise RuntimeError(f"環境変数が未設定です: {e}")
```

- [ ] **Step 6: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_config.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: コミット**

```bash
git add 株自動売買bot/
git commit -m "feat(stock-bot): project scaffold and config"
```

---

### Task 2: ドメイン型（Position / Signal）

**Files:**
- Create: `株自動売買bot/domain.py`
- Create: `株自動売買bot/tests/test_domain.py`

**Interfaces:**
- Produces:
  - `Signal` (Enum): `BUY`, `SELL`, `HOLD`
  - `Position` dataclass: `symbol:str, qty:float, avg_entry_price:float`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_domain.py`:
```python
from domain import Signal, Position

def test_signal_values():
    assert Signal.BUY.value == "BUY"
    assert Signal.SELL.value == "SELL"
    assert Signal.HOLD.value == "HOLD"

def test_position_fields():
    p = Position(symbol="AAPL", qty=10, avg_entry_price=150.0)
    assert p.symbol == "AAPL" and p.qty == 10 and p.avg_entry_price == 150.0
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_domain.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'domain'`)

- [ ] **Step 3: domain.py を実装**

```python
from dataclasses import dataclass
from enum import Enum

class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_domain.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/domain.py 株自動売買bot/tests/test_domain.py
git commit -m "feat(stock-bot): domain types (Signal, Position)"
```

---

### Task 3: 戦略（strategy.py, 純粋関数）

**Files:**
- Create: `株自動売買bot/strategy.py`
- Create: `株自動売買bot/tests/test_strategy.py`

**Interfaces:**
- Consumes: `config.StrategyParams`, `domain.Signal`, `domain.Position`
- Produces:
  - `compute_ema(closes: pd.Series, span: int) -> pd.Series`
  - `decide_signal(bars: pd.DataFrame, position: Optional[Position], params: StrategyParams, force_flatten: bool=False) -> Signal`
    - `bars`: 昇順の DataFrame。列 `["open","high","low","close","volume"]`。
    - `force_flatten=True` かつ保有ありなら常に `SELL`（クローズ前手仕舞い用）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_strategy.py`:
```python
import pandas as pd
import numpy as np
from strategy import compute_ema, decide_signal
from domain import Signal, Position
from config import StrategyParams

def make_bars(closes):
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1000]*len(closes),
    })

def test_compute_ema_length():
    s = pd.Series([1.0,2,3,4,5])
    ema = compute_ema(s, 3)
    assert len(ema) == 5

def test_hold_when_not_enough_bars():
    bars = make_bars([1.0,2,3])
    p = StrategyParams(ema_fast=9, ema_slow=21)
    assert decide_signal(bars, None, p) == Signal.HOLD

def test_buy_on_golden_cross_with_positive_momentum():
    # 下降→反発で短期EMAが長期EMAを上抜けする系列
    closes = [10]*20 + [9,8,7,6,5,6,8,11,15,20]
    bars = make_bars([float(c) for c in closes])
    p = StrategyParams(ema_fast=3, ema_slow=8, stop_loss_pct=0.02, take_profit_pct=0.04)
    assert decide_signal(bars, None, p) == Signal.BUY

def test_sell_on_stop_loss():
    closes = [float(c) for c in range(1, 40)]  # 上昇トレンド
    bars = make_bars(closes)
    # entry を現値より十分高くして損切り発火
    pos = Position("AAPL", qty=10, avg_entry_price=bars["close"].iloc[-1] * 1.10)
    p = StrategyParams(ema_fast=3, ema_slow=8, stop_loss_pct=0.02, take_profit_pct=0.20)
    assert decide_signal(bars, pos, p) == Signal.SELL

def test_sell_on_take_profit():
    closes = [float(c) for c in range(1, 40)]
    bars = make_bars(closes)
    pos = Position("AAPL", qty=10, avg_entry_price=bars["close"].iloc[-1] * 0.90)
    p = StrategyParams(ema_fast=3, ema_slow=8, stop_loss_pct=0.50, take_profit_pct=0.04)
    assert decide_signal(bars, pos, p) == Signal.SELL

def test_force_flatten_sells_when_held():
    bars = make_bars([float(c) for c in range(1, 40)])
    pos = Position("AAPL", qty=10, avg_entry_price=1.0)
    p = StrategyParams()
    assert decide_signal(bars, pos, p, force_flatten=True) == Signal.SELL

def test_force_flatten_holds_when_flat():
    bars = make_bars([float(c) for c in range(1, 40)])
    p = StrategyParams()
    assert decide_signal(bars, None, p, force_flatten=True) == Signal.HOLD
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_strategy.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'strategy'`)

- [ ] **Step 3: strategy.py を実装**

```python
from typing import Optional
import pandas as pd
from domain import Signal, Position
from config import StrategyParams

def compute_ema(closes: pd.Series, span: int) -> pd.Series:
    return closes.ewm(span=span, adjust=False).mean()

def decide_signal(
    bars: pd.DataFrame,
    position: Optional[Position],
    params: StrategyParams,
    force_flatten: bool = False,
) -> Signal:
    if force_flatten:
        return Signal.SELL if position is not None else Signal.HOLD

    closes = bars["close"]
    if len(closes) < params.ema_slow + 1:
        return Signal.HOLD

    ema_fast = compute_ema(closes, params.ema_fast)
    ema_slow = compute_ema(closes, params.ema_slow)
    price = float(closes.iloc[-1])

    cross_up = ema_fast.iloc[-2] <= ema_slow.iloc[-2] and ema_fast.iloc[-1] > ema_slow.iloc[-1]
    cross_down = ema_fast.iloc[-2] >= ema_slow.iloc[-2] and ema_fast.iloc[-1] < ema_slow.iloc[-1]
    momentum_up = closes.iloc[-1] > closes.iloc[-2]

    if position is None:
        if cross_up and momentum_up:
            return Signal.BUY
        return Signal.HOLD

    entry = position.avg_entry_price
    if price <= entry * (1 - params.stop_loss_pct):
        return Signal.SELL
    if price >= entry * (1 + params.take_profit_pct):
        return Signal.SELL
    if cross_down:
        return Signal.SELL
    return Signal.HOLD
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_strategy.py -v`
Expected: PASS (7 passed)。もし `test_buy_on_golden_cross_with_positive_momentum` が FAIL する場合は系列を調整（EMA本数に対して十分な上抜けが起きるように），ロジックは変えない。

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/strategy.py 株自動売買bot/tests/test_strategy.py
git commit -m "feat(stock-bot): EMA-cross strategy (pure function)"
```

---

### Task 4: リスク管理（risk.py, 純粋関数）

**Files:**
- Create: `株自動売買bot/risk.py`
- Create: `株自動売買bot/tests/test_risk.py`

**Interfaces:**
- Consumes: `config.RiskParams`
- Produces:
  - `calc_qty(equity: float, price: float, position_pct: float) -> int` — `floor(equity*pct/price)`、0 以下は 0。
  - `can_open(current_positions: int, max_positions: int, cash: float, cost: float) -> bool`
  - `daily_loss_exceeded(start_equity: float, current_equity: float, daily_max_loss_pct: float) -> bool`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_risk.py`:
```python
from risk import calc_qty, can_open, daily_loss_exceeded

def test_calc_qty_floors():
    assert calc_qty(equity=10000, price=150, position_pct=0.10) == 6  # 1000/150=6.67->6

def test_calc_qty_zero_when_too_expensive():
    assert calc_qty(equity=100, price=150, position_pct=0.10) == 0

def test_can_open_true():
    assert can_open(current_positions=2, max_positions=5, cash=1000, cost=900) is True

def test_can_open_false_when_max_positions():
    assert can_open(current_positions=5, max_positions=5, cash=1000, cost=100) is False

def test_can_open_false_when_insufficient_cash():
    assert can_open(current_positions=1, max_positions=5, cash=500, cost=900) is False

def test_daily_loss_exceeded_true():
    assert daily_loss_exceeded(start_equity=10000, current_equity=9400, daily_max_loss_pct=0.05) is True

def test_daily_loss_exceeded_false():
    assert daily_loss_exceeded(start_equity=10000, current_equity=9600, daily_max_loss_pct=0.05) is False
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_risk.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'risk'`)

- [ ] **Step 3: risk.py を実装**

```python
import math

def calc_qty(equity: float, price: float, position_pct: float) -> int:
    if price <= 0:
        return 0
    qty = math.floor((equity * position_pct) / price)
    return max(qty, 0)

def can_open(current_positions: int, max_positions: int, cash: float, cost: float) -> bool:
    if current_positions >= max_positions:
        return False
    if cost > cash:
        return False
    return True

def daily_loss_exceeded(start_equity: float, current_equity: float, daily_max_loss_pct: float) -> bool:
    if start_equity <= 0:
        return False
    loss_pct = (start_equity - current_equity) / start_equity
    return loss_pct >= daily_max_loss_pct
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_risk.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/risk.py 株自動売買bot/tests/test_risk.py
git commit -m "feat(stock-bot): risk sizing and limits"
```

---

### Task 5: 記録（journal.py）

**Files:**
- Create: `株自動売買bot/journal.py`
- Create: `株自動売買bot/tests/test_journal.py`

**Interfaces:**
- Produces:
  - `record_trade(path: str, trade: dict) -> None` — CSV 追記。`trade` キー: `timestamp, symbol, side, qty, price`。
  - `read_trades(path: str) -> list[dict]`
  - `summarize(trades: list[dict]) -> dict` — キー: `num_trades:int, realized_pnl:float, win_rate:float`。
    実現損益は同一銘柄の BUY→SELL を FIFO で突き合わせて算出。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_journal.py`:
```python
import os
from journal import record_trade, read_trades, summarize

def test_record_and_read(tmp_path):
    p = str(tmp_path / "j.csv")
    record_trade(p, {"timestamp":"t1","symbol":"AAPL","side":"BUY","qty":10,"price":100.0})
    record_trade(p, {"timestamp":"t2","symbol":"AAPL","side":"SELL","qty":10,"price":110.0})
    rows = read_trades(p)
    assert len(rows) == 2 and rows[0]["symbol"] == "AAPL"

def test_summarize_realized_pnl_and_winrate():
    trades = [
        {"timestamp":"t1","symbol":"AAPL","side":"BUY","qty":10,"price":100.0},
        {"timestamp":"t2","symbol":"AAPL","side":"SELL","qty":10,"price":110.0},  # +100 (win)
        {"timestamp":"t3","symbol":"MSFT","side":"BUY","qty":5,"price":200.0},
        {"timestamp":"t4","symbol":"MSFT","side":"SELL","qty":5,"price":180.0},   # -100 (loss)
    ]
    s = summarize(trades)
    assert s["num_trades"] == 4
    assert abs(s["realized_pnl"] - 0.0) < 1e-9
    assert abs(s["win_rate"] - 0.5) < 1e-9
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_journal.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'journal'`)

- [ ] **Step 3: journal.py を実装**

```python
import csv
import os
from collections import defaultdict, deque

FIELDS = ["timestamp", "symbol", "side", "qty", "price"]

def record_trade(path: str, trade: dict) -> None:
    exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow({k: trade[k] for k in FIELDS})

def read_trades(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))

def summarize(trades: list) -> dict:
    lots = defaultdict(deque)   # symbol -> deque of (qty, price) from BUYs
    realized = 0.0
    wins = 0
    closed = 0
    for t in trades:
        sym = t["symbol"]
        side = t["side"]
        qty = float(t["qty"])
        price = float(t["price"])
        if side == "BUY":
            lots[sym].append([qty, price])
        elif side == "SELL":
            remaining = qty
            while remaining > 0 and lots[sym]:
                lot = lots[sym][0]
                matched = min(remaining, lot[0])
                pnl = (price - lot[1]) * matched
                realized += pnl
                closed += 1
                if pnl > 0:
                    wins += 1
                lot[0] -= matched
                remaining -= matched
                if lot[0] <= 0:
                    lots[sym].popleft()
    win_rate = (wins / closed) if closed else 0.0
    return {"num_trades": len(trades), "realized_pnl": realized, "win_rate": win_rate}
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_journal.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/journal.py 株自動売買bot/tests/test_journal.py
git commit -m "feat(stock-bot): trade journal and P&L summary"
```

---

### Task 6: Slack通知（notifier.py）

**Files:**
- Create: `株自動売買bot/notifier.py`
- Create: `株自動売買bot/tests/test_notifier.py`

**Interfaces:**
- Produces:
  - `send_slack(webhook_url: str, text: str, *, session=None) -> bool` — 例外を握って `False` を返す（通知失敗が本体を止めない）。`session` は DI 用（未指定なら `requests`）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_notifier.py`:
```python
from unittest.mock import MagicMock
from notifier import send_slack

def test_send_slack_posts_payload():
    sess = MagicMock()
    sess.post.return_value = MagicMock(status_code=200)
    ok = send_slack("http://hook", "hello", session=sess)
    assert ok is True
    sess.post.assert_called_once()
    args, kwargs = sess.post.call_args
    assert kwargs["json"] == {"text": "hello"}

def test_send_slack_returns_false_on_exception():
    sess = MagicMock()
    sess.post.side_effect = RuntimeError("network down")
    ok = send_slack("http://hook", "hi", session=sess)
    assert ok is False
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_notifier.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'notifier'`)

- [ ] **Step 3: notifier.py を実装**

```python
import requests

def send_slack(webhook_url: str, text: str, *, session=None) -> bool:
    client = session or requests
    try:
        resp = client.post(webhook_url, json={"text": text}, timeout=10)
        return getattr(resp, "status_code", 200) == 200
    except Exception:
        return False
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_notifier.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/notifier.py 株自動売買bot/tests/test_notifier.py
git commit -m "feat(stock-bot): Slack notifier"
```

---

### Task 7: データ取得（data.py, Alpacaラッパ）

**Files:**
- Create: `株自動売買bot/data.py`
- Create: `株自動売買bot/tests/test_data.py`

**Interfaces:**
- Consumes: `config.Credentials`
- Produces:
  - `class MarketData` — コンストラクタ `MarketData(key, secret, client=None)`（`client` は DI 用、未指定なら `alpaca.data.historical.StockHistoricalDataClient`）。
  - `MarketData.get_bars(symbols: list[str], start, end, minutes: int=5) -> dict[str, pd.DataFrame]` — 各 DataFrame は昇順、列 `["open","high","low","close","volume"]`。
  - `_bars_to_df(alpaca_bars_for_symbol) -> pd.DataFrame`（内部変換、テスト対象）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_data.py`:
```python
import pandas as pd
from types import SimpleNamespace
from data import _bars_to_df

def test_bars_to_df_sorted_columns():
    raw = [
        SimpleNamespace(timestamp=2, open=2, high=3, low=1, close=2.5, volume=100),
        SimpleNamespace(timestamp=1, open=1, high=2, low=0.5, close=1.5, volume=90),
    ]
    df = _bars_to_df(raw)
    assert list(df.columns) == ["open","high","low","close","volume"]
    # 昇順（timestamp=1 が先頭）
    assert df["close"].iloc[0] == 1.5
    assert df["close"].iloc[1] == 2.5
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_data.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'data'`)

- [ ] **Step 3: data.py を実装**

```python
from typing import Optional
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

def _bars_to_df(raw_bars) -> pd.DataFrame:
    rows = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in raw_bars
    ]
    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df[["open", "high", "low", "close", "volume"]]

class MarketData:
    def __init__(self, key: str, secret: str, client=None):
        self._client = client or StockHistoricalDataClient(key, secret)

    def get_bars(self, symbols, start, end, minutes: int = 5) -> dict:
        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(minutes, TimeFrameUnit.Minute),
            start=start,
            end=end,
        )
        resp = self._client.get_stock_bars(req)
        out = {}
        for sym in symbols:
            raw = resp.data.get(sym, []) if hasattr(resp, "data") else []
            out[sym] = _bars_to_df(raw)
        return out
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_data.py -v`
Expected: PASS。import エラーが出る場合は alpaca-py の実際のモジュールパスに合わせて import を修正（`_bars_to_df` のテストは import さえ通れば PASS）。

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/data.py 株自動売買bot/tests/test_data.py
git commit -m "feat(stock-bot): Alpaca market-data wrapper"
```

---

### Task 8: 発注（broker.py, Alpacaラッパ・ペーパー固定）

**Files:**
- Create: `株自動売買bot/broker.py`
- Create: `株自動売買bot/tests/test_broker.py`

**Interfaces:**
- Consumes: `domain.Position`
- Produces:
  - `class Broker` — `Broker(key, secret, paper=True, client=None)`（`client` は DI 用、未指定なら `alpaca.trading.client.TradingClient(key, secret, paper=paper)`）。
  - `Broker.get_equity() -> float`
  - `Broker.get_cash() -> float`
  - `Broker.get_positions() -> dict[str, Position]`
  - `Broker.is_market_open() -> bool`
  - `Broker.submit_market_order(symbol: str, qty: float, side: str) -> None` — `side` は `"BUY"`/`"SELL"`。
  - `Broker.close_all_positions() -> None`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_broker.py`:
```python
from types import SimpleNamespace
from unittest.mock import MagicMock
from broker import Broker
from domain import Position

def make_broker(client):
    return Broker("k", "s", paper=True, client=client)

def test_get_equity():
    client = MagicMock()
    client.get_account.return_value = SimpleNamespace(equity="10000", cash="5000")
    assert make_broker(client).get_equity() == 10000.0

def test_get_positions_maps_to_domain():
    client = MagicMock()
    client.get_all_positions.return_value = [
        SimpleNamespace(symbol="AAPL", qty="10", avg_entry_price="150.0")
    ]
    positions = make_broker(client).get_positions()
    assert positions["AAPL"] == Position("AAPL", 10.0, 150.0)

def test_is_market_open():
    client = MagicMock()
    client.get_clock.return_value = SimpleNamespace(is_open=True)
    assert make_broker(client).is_market_open() is True

def test_submit_market_order_buy_calls_client():
    client = MagicMock()
    make_broker(client).submit_market_order("AAPL", 5, "BUY")
    client.submit_order.assert_called_once()
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_broker.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'broker'`)

- [ ] **Step 3: broker.py を実装**

```python
from domain import Position
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

class Broker:
    def __init__(self, key: str, secret: str, paper: bool = True, client=None):
        self._client = client or TradingClient(key, secret, paper=paper)

    def get_equity(self) -> float:
        return float(self._client.get_account().equity)

    def get_cash(self) -> float:
        return float(self._client.get_account().cash)

    def get_positions(self) -> dict:
        out = {}
        for p in self._client.get_all_positions():
            out[p.symbol] = Position(p.symbol, float(p.qty), float(p.avg_entry_price))
        return out

    def is_market_open(self) -> bool:
        return bool(self._client.get_clock().is_open)

    def submit_market_order(self, symbol: str, qty: float, side: str) -> None:
        order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=symbol, qty=qty, side=order_side, time_in_force=TimeInForce.DAY
        )
        self._client.submit_order(req)

    def close_all_positions(self) -> None:
        self._client.close_all_positions(cancel_orders=True)
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_broker.py -v`
Expected: PASS (4 passed)。import パスが違う場合は alpaca-py の実モジュールに合わせて修正。

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/broker.py 株自動売買bot/tests/test_broker.py
git commit -m "feat(stock-bot): Alpaca paper broker wrapper"
```

---

### Task 9: バックテスト（backtest.py）

**Files:**
- Create: `株自動売買bot/backtest.py`
- Create: `株自動売買bot/tests/test_backtest.py`

**Interfaces:**
- Consumes: `strategy.decide_signal`, `domain.Signal/Position`, `config.StrategyParams`
- Produces:
  - `run_backtest(bars: pd.DataFrame, params: StrategyParams, min_bars: int, cash: float=10000.0) -> dict` — 単一銘柄・全額投入の簡易バックテスト。バーを1本ずつ increment して `decide_signal` を呼び、BUY で全額購入、SELL で全売却。
    戻り: `{"total_return": float, "num_trades": int, "win_rate": float, "max_drawdown": float}`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_backtest.py`:
```python
import pandas as pd
from backtest import run_backtest
from config import StrategyParams

def make_bars(closes):
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1000]*len(closes),
    })

def test_backtest_no_trades_flat_series():
    bars = make_bars([100.0]*60)
    p = StrategyParams(ema_fast=3, ema_slow=8)
    res = run_backtest(bars, p, min_bars=9)
    assert res["num_trades"] == 0
    assert res["total_return"] == 0.0

def test_backtest_returns_expected_keys():
    closes = [10.0]*20 + [9,8,7,6,5,6,8,11,15,20,22,24,26,28,30]
    bars = make_bars([float(c) for c in closes])
    p = StrategyParams(ema_fast=3, ema_slow=8, stop_loss_pct=0.5, take_profit_pct=0.5)
    res = run_backtest(bars, p, min_bars=9)
    assert set(res.keys()) == {"total_return","num_trades","win_rate","max_drawdown"}
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_backtest.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'backtest'`)

- [ ] **Step 3: backtest.py を実装**

```python
from typing import Optional
import pandas as pd
from strategy import decide_signal
from domain import Signal, Position
from config import StrategyParams

def run_backtest(bars: pd.DataFrame, params: StrategyParams, min_bars: int, cash: float = 10000.0) -> dict:
    start_cash = cash
    position: Optional[Position] = None
    qty = 0.0
    num_trades = 0
    wins = 0
    closed = 0
    equity_curve = []

    for i in range(min_bars, len(bars) + 1):
        window = bars.iloc[:i].reset_index(drop=True)
        price = float(window["close"].iloc[-1])
        sig = decide_signal(window, position, params)

        if sig == Signal.BUY and position is None:
            qty = cash / price
            position = Position("BT", qty, price)
            cash = 0.0
            num_trades += 1
        elif sig == Signal.SELL and position is not None:
            proceeds = qty * price
            pnl = proceeds - qty * position.avg_entry_price
            cash = proceeds
            closed += 1
            if pnl > 0:
                wins += 1
            position = None
            qty = 0.0
            num_trades += 1

        equity = cash + (qty * price if position else 0.0)
        equity_curve.append(equity)

    # 最終評価（未決済は最終価格で評価）
    final_equity = cash + (qty * float(bars["close"].iloc[-1]) if position else 0.0)
    total_return = (final_equity - start_cash) / start_cash

    peak = start_cash
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        dd = (peak - e) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    win_rate = (wins / closed) if closed else 0.0
    return {
        "total_return": total_return,
        "num_trades": num_trades,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
    }
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_backtest.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: コミット**

```bash
git add 株自動売買bot/backtest.py 株自動売買bot/tests/test_backtest.py
git commit -m "feat(stock-bot): single-symbol backtester"
```

---

### Task 10: 本番ループ（run_live.py）

**Files:**
- Create: `株自動売買bot/run_live.py`
- Create: `株自動売買bot/tests/test_run_live.py`

**Interfaces:**
- Consumes: `config`, `data.MarketData`, `strategy.decide_signal`, `risk`, `broker.Broker`, `journal`, `notifier`, `domain`
- Produces:
  - `run_cycle(broker, market_data, params, risk_params, symbols, journal_path, webhook, *, force_flatten=False, start_equity=None, now=None) -> list[dict]` — 1 サイクル分の判定＋発注を行い、実行したトレードの一覧を返す（テスト可能な純粋寄りの関数。IO はモック）。
  - `main() -> None` — 認証読み込み→市場オープン中のみ 5 分間隔ループ→クローズ 15 分前で `force_flatten=True`→日次損失超過で新規停止。`__main__` から呼ぶ。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_run_live.py`:
```python
import pandas as pd
from unittest.mock import MagicMock
from run_live import run_cycle
from domain import Position
from config import StrategyParams, RiskParams

def make_bars(closes):
    return pd.DataFrame({
        "open": closes, "high": closes, "low": closes,
        "close": closes, "volume": [1000]*len(closes),
    })

def test_run_cycle_buys_on_signal(tmp_path):
    # 上抜けする系列
    closes = [10.0]*20 + [9,8,7,6,5,6,8,11,15,20]
    bars = make_bars([float(c) for c in closes])

    broker = MagicMock()
    broker.get_equity.return_value = 10000.0
    broker.get_cash.return_value = 10000.0
    broker.get_positions.return_value = {}   # フラット

    md = MagicMock()
    md.get_bars.return_value = {"AAPL": bars}

    p = StrategyParams(ema_fast=3, ema_slow=8)
    r = RiskParams(max_positions=5, position_pct=0.10)

    trades = run_cycle(
        broker, md, p, r, ["AAPL"],
        journal_path=str(tmp_path/"j.csv"), webhook="",
        start_equity=10000.0,
    )
    assert any(t["side"] == "BUY" and t["symbol"] == "AAPL" for t in trades)
    broker.submit_market_order.assert_called()

def test_run_cycle_force_flatten_sells_held(tmp_path):
    bars = make_bars([float(c) for c in range(1, 40)])
    broker = MagicMock()
    broker.get_equity.return_value = 10000.0
    broker.get_cash.return_value = 0.0
    broker.get_positions.return_value = {"AAPL": Position("AAPL", 10, 100.0)}
    md = MagicMock()
    md.get_bars.return_value = {"AAPL": bars}

    trades = run_cycle(
        broker, md, StrategyParams(), RiskParams(), ["AAPL"],
        journal_path=str(tmp_path/"j.csv"), webhook="",
        force_flatten=True, start_equity=10000.0,
    )
    assert any(t["side"] == "SELL" for t in trades)

def test_run_cycle_halts_new_buys_on_daily_loss(tmp_path):
    closes = [10.0]*20 + [9,8,7,6,5,6,8,11,15,20]
    bars = make_bars([float(c) for c in closes])
    broker = MagicMock()
    broker.get_equity.return_value = 9000.0   # -10% < -5% 閾値
    broker.get_cash.return_value = 9000.0
    broker.get_positions.return_value = {}
    md = MagicMock()
    md.get_bars.return_value = {"AAPL": bars}

    trades = run_cycle(
        broker, md, StrategyParams(ema_fast=3, ema_slow=8),
        RiskParams(daily_max_loss_pct=0.05), ["AAPL"],
        journal_path=str(tmp_path/"j.csv"), webhook="",
        start_equity=10000.0,
    )
    assert all(t["side"] != "BUY" for t in trades)
```

- [ ] **Step 2: 実行して失敗を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_run_live.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'run_live'`)

- [ ] **Step 3: run_live.py を実装**

```python
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import config
from data import MarketData
from broker import Broker
from strategy import decide_signal
from domain import Signal
import risk
import journal
from notifier import send_slack

def run_cycle(broker, market_data, params, risk_params, symbols, journal_path, webhook,
              *, force_flatten=False, start_equity=None, now=None) -> list:
    now = now or datetime.now(timezone.utc)
    equity = broker.get_equity()
    cash = broker.get_cash()
    positions = broker.get_positions()
    executed = []

    halt_new = False
    if start_equity is not None and risk.daily_loss_exceeded(
        start_equity, equity, risk_params.daily_max_loss_pct
    ):
        halt_new = True

    lookback_start = now - timedelta(minutes=config.TIMEFRAME_MINUTES * 300)
    bars_by_symbol = market_data.get_bars(symbols, lookback_start, now, config.TIMEFRAME_MINUTES)

    for sym in symbols:
        bars = bars_by_symbol.get(sym)
        if bars is None or len(bars) == 0:
            continue
        pos = positions.get(sym)
        sig = decide_signal(bars, pos, params, force_flatten=force_flatten)
        price = float(bars["close"].iloc[-1])

        if sig == Signal.BUY and pos is None and not halt_new:
            qty = risk.calc_qty(equity, price, risk_params.position_pct)
            cost = qty * price
            if qty > 0 and risk.can_open(len(positions), risk_params.max_positions, cash, cost):
                broker.submit_market_order(sym, qty, "BUY")
                cash -= cost
                positions[sym] = None  # 保有数カウント用の暫定
                trade = {"timestamp": now.isoformat(), "symbol": sym, "side": "BUY",
                         "qty": qty, "price": price}
                executed.append(trade)
                journal.record_trade(journal_path, trade)
                if webhook:
                    send_slack(webhook, f"BUY {sym} x{qty} @ {price:.2f}")
        elif sig == Signal.SELL and pos is not None:
            broker.submit_market_order(sym, pos.qty, "SELL")
            trade = {"timestamp": now.isoformat(), "symbol": sym, "side": "SELL",
                     "qty": pos.qty, "price": price}
            executed.append(trade)
            journal.record_trade(journal_path, trade)
            if webhook:
                send_slack(webhook, f"SELL {sym} x{pos.qty} @ {price:.2f}")

    return executed

def main() -> None:
    creds = config.load_credentials()
    broker = Broker(creds.alpaca_key, creds.alpaca_secret, paper=True)
    market_data = MarketData(creds.alpaca_key, creds.alpaca_secret)
    params = config.StrategyParams()
    risk_params = config.RiskParams()
    journal_path = "journal_paper.csv"

    start_equity = None
    day_marker = None

    while True:
        try:
            if not broker.is_market_open():
                time.sleep(60)
                continue
            now = datetime.now(timezone.utc)
            today = now.date()
            if day_marker != today:
                start_equity = broker.get_equity()
                day_marker = today
                send_slack(creds.slack_webhook, f"[stock-bot] 稼働開始 equity={start_equity}")

            # クローズ判定（Alpaca clock の next_close を利用）
            clock = broker._client.get_clock()
            close_at = getattr(clock, "next_close", None)
            force_flatten = False
            if close_at is not None:
                remaining = (close_at - now).total_seconds() / 60.0
                force_flatten = remaining <= config.FLATTEN_BEFORE_CLOSE_MIN

            run_cycle(broker, market_data, params, risk_params, config.SYMBOLS,
                      journal_path, creds.slack_webhook,
                      force_flatten=force_flatten, start_equity=start_equity, now=now)

            trades = journal.read_trades(journal_path)
            summary = journal.summarize(trades)
            print(f"{now.isoformat()} summary={summary}")
        except Exception as e:
            send_slack(creds.slack_webhook, f"[stock-bot] エラーで停止: {e}")
            raise
        time.sleep(config.TIMEFRAME_MINUTES * 60)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 実行して成功を確認**

Run: `cd 株自動売買bot && ./.venv/bin/pytest tests/test_run_live.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 全テストを実行**

Run: `cd 株自動売買bot && ./.venv/bin/pytest -v`
Expected: 全 PASS

- [ ] **Step 6: コミット**

```bash
git add 株自動売買bot/run_live.py 株自動売買bot/tests/test_run_live.py
git commit -m "feat(stock-bot): live trading loop with daily-loss halt and flatten"
```

---

### Task 11: 実行手順ドキュメント（README）

**Files:**
- Create: `株自動売買bot/README.md`

**Interfaces:** なし（ドキュメントのみ）

- [ ] **Step 1: README を作成**

内容:
- 概要（ペーパートレード専用であること）
- セットアップ: venv 作成、`pip install -r requirements.txt`
- Alpaca ペーパー口座の API キー取得手順（https://app.alpaca.markets/ でペーパーキー発行）
- Slack Incoming Webhook の作り方（URL 発行→`.env` に貼る）
- `.env` を `.env.example` からコピーして値を入れる
- バックテストの回し方（例スクリプト）
- 本番ループの起動: `./.venv/bin/python run_live.py`（米国市場時間中・Mac をスリープさせない `caffeinate -i` の案内）
- パラメータ変更のしかた（`config.py`）
- 免責: 投資は自己責任、まずペーパーで検証

- [ ] **Step 2: コミット**

```bash
git add 株自動売買bot/README.md
git commit -m "docs(stock-bot): setup and run guide"
```

---

## 実装後の確認（キー投入が必要な段階）

Task 1〜11 はすべて **モック/fixture でテストが通り、実 API キー不要**で完成する。
実際にペーパー口座へ接続して動かすには、ユーザーに以下を用意してもらう必要がある（重要な意思決定・外部連携のためここで一旦確認）:
- Alpaca ペーパー口座の API キー / シークレット
- Slack Incoming Webhook URL

これらを `.env` に設定後、`run_live.py` を米国市場時間中に起動して数日試走 → `journal_paper.csv` と Slack で成績レビュー。
