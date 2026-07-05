from dataclasses import dataclass
import os


@dataclass
class StrategyParams:
    ema_fast: int = 9
    ema_slow: int = 21
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04


@dataclass
class RiskParams:
    max_positions: int = 5
    position_pct: float = 0.10
    daily_max_loss_pct: float = 0.05


@dataclass
class Credentials:
    alpaca_key: str
    alpaca_secret: str
    slack_webhook: str


SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "JPM"]
TIMEFRAME_MINUTES = 5
FLATTEN_BEFORE_CLOSE_MIN = 15


def load_credentials() -> Credentials:
    try:
        return Credentials(
            alpaca_key=os.environ["ALPACA_API_KEY"],
            alpaca_secret=os.environ["ALPACA_SECRET_KEY"],
            slack_webhook=os.environ["SLACK_WEBHOOK_URL"],
        )
    except KeyError as e:
        raise RuntimeError(f"環境変数が未設定です: {e}")
