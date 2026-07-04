from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "race.db"

USER_AGENT = "keiba-research/0.1 (personal study; contact: local)"
SLEEP_MIN = 2.0
SLEEP_MAX = 4.0

# 収集対象期間（JRA中央・直近5年）。実行時に上書き可能。
DATE_START = "2021-01-01"
DATE_END = "2025-12-31"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
