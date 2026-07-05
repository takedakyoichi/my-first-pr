import pandas as pd
from types import SimpleNamespace
from data import _bars_to_df

def test_bars_to_df_sorted_columns():
    raw = [
        SimpleNamespace(timestamp=2, open=2, high=3, low=1, close=2.5, volume=100),
        SimpleNamespace(timestamp=1, open=1, high=2, low=0.5, close=1.5, volume=90),
    ]
    df = _bars_to_df(raw)
    assert list(df.columns) == ["open","high","low","close","volume"]
    assert df["close"].iloc[0] == 1.5
    assert df["close"].iloc[1] == 2.5
