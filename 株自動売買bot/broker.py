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
