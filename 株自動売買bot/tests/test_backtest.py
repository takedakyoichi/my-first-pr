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
