import time
from datetime import datetime, timedelta, timezone

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
