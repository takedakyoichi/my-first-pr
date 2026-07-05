from risk import calc_qty, can_open, daily_loss_exceeded

def test_calc_qty_floors():
    assert calc_qty(equity=10000, price=150, position_pct=0.10) == 6  # 1000/150=6.67->6

def test_calc_qty_zero_when_too_expensive():
    assert calc_qty(equity=100, price=150, position_pct=0.10) == 0

def test_can_open_true():
    assert can_open(current_positions=2, max_positions=5, cash=1000, cost=900) is True

def test_can_open_false_when_max_positions():
    assert can_open(current_positions=5, max_positions=5, cash=1000, cost=100) is False

def test_can_open_false_when_insufficient_cash():
    assert can_open(current_positions=1, max_positions=5, cash=500, cost=900) is False

def test_daily_loss_exceeded_true():
    assert daily_loss_exceeded(start_equity=10000, current_equity=9400, daily_max_loss_pct=0.05) is True

def test_daily_loss_exceeded_false():
    assert daily_loss_exceeded(start_equity=10000, current_equity=9600, daily_max_loss_pct=0.05) is False
