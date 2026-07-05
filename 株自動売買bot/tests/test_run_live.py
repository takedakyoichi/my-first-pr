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
    closes = [10.0]*25 + [9,8,7,6,5,6,7,8,9]
    bars = make_bars([float(c) for c in closes])

    broker = MagicMock()
    broker.get_equity.return_value = 10000.0
    broker.get_cash.return_value = 10000.0
    broker.get_positions.return_value = {}

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
    closes = [10.0]*25 + [9,8,7,6,5,6,7,8,9]
    bars = make_bars([float(c) for c in closes])
    broker = MagicMock()
    broker.get_equity.return_value = 9000.0
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
