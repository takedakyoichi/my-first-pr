import os
from journal import record_trade, read_trades, summarize

def test_record_and_read(tmp_path):
    p = str(tmp_path / "j.csv")
    record_trade(p, {"timestamp":"t1","symbol":"AAPL","side":"BUY","qty":10,"price":100.0})
    record_trade(p, {"timestamp":"t2","symbol":"AAPL","side":"SELL","qty":10,"price":110.0})
    rows = read_trades(p)
    assert len(rows) == 2 and rows[0]["symbol"] == "AAPL"

def test_summarize_realized_pnl_and_winrate():
    trades = [
        {"timestamp":"t1","symbol":"AAPL","side":"BUY","qty":10,"price":100.0},
        {"timestamp":"t2","symbol":"AAPL","side":"SELL","qty":10,"price":110.0},  # +100 (win)
        {"timestamp":"t3","symbol":"MSFT","side":"BUY","qty":5,"price":200.0},
        {"timestamp":"t4","symbol":"MSFT","side":"SELL","qty":5,"price":180.0},   # -100 (loss)
    ]
    s = summarize(trades)
    assert s["num_trades"] == 4
    assert abs(s["realized_pnl"] - 0.0) < 1e-9
    assert abs(s["win_rate"] - 0.5) < 1e-9
