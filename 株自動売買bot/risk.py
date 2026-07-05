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
