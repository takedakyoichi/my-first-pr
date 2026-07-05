import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit


def _bars_to_df(raw_bars) -> pd.DataFrame:
    rows = [
        {"timestamp": b.timestamp, "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in raw_bars
    ]
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df[["open", "high", "low", "close", "volume"]]


class MarketData:
    def __init__(self, key: str, secret: str, client=None):
        self._client = client or StockHistoricalDataClient(key, secret)

    def get_bars(self, symbols, start, end, minutes: int = 5) -> dict:
        req = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame(minutes, TimeFrameUnit.Minute),
            start=start,
            end=end,
        )
        resp = self._client.get_stock_bars(req)
        out = {}
        for sym in symbols:
            raw = resp.data.get(sym, []) if hasattr(resp, "data") else []
            out[sym] = _bars_to_df(raw)
        return out
