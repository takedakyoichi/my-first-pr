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
    lots = defaultdict(deque)  # symbol -> deque of [qty, price] from BUYs
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
