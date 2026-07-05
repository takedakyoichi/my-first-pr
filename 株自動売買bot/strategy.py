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
