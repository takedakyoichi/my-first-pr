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
    # 上抜けがちょうど最終バーで起きる系列（フラット→ディップ→緩やかに回復）
    closes = [10]*25 + [9,8,7,6,5,6,7,8,9]
    bars = make_bars([float(c) for c in closes])
    p = StrategyParams(ema_fast=3, ema_slow=8, stop_loss_pct=0.02, take_profit_pct=0.04)
    assert decide_signal(bars, None, p) == Signal.BUY

def test_sell_on_stop_loss():
    closes = [float(c) for c in range(1, 40)]
    bars = make_bars(closes)
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
