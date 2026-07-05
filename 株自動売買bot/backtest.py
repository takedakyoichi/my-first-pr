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
