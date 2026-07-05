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
