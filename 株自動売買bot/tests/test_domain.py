from domain import Signal, Position

def test_signal_values():
    assert Signal.BUY.value == "BUY"
    assert Signal.SELL.value == "SELL"
    assert Signal.HOLD.value == "HOLD"

def test_position_fields():
    p = Position(symbol="AAPL", qty=10, avg_entry_price=150.0)
    assert p.symbol == "AAPL" and p.qty == 10 and p.avg_entry_price == 150.0
