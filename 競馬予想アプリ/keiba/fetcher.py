import hashlib
import random
import time
from pathlib import Path

import requests

from keiba import config


def _default_sleeper():
    time.sleep(random.uniform(config.SLEEP_MIN, config.SLEEP_MAX))


def cache_path(url: str) -> Path:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return config.CACHE_DIR / f"{h}.html"


def fetch(url, *, encoding="euc-jp", session=None, sleeper=None, max_retries=3, backoff_sleep=None) -> str:
    path = cache_path(url)
    if path.exists():
        return path.read_bytes().decode(encoding, errors="replace")

    sess = session or requests.Session()
    sleeper = sleeper or _default_sleeper
    backoff_sleep = backoff_sleep or time.sleep
    headers = {"User-Agent": config.USER_AGENT}

    delay = 1.0
    last_exc = None
    for _ in range(max_retries):
        sleeper()  # 取得の前に必ず待つ（礼儀）
        try:
            resp = sess.get(url, headers=headers, timeout=30)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exc = RuntimeError(f"status {resp.status_code}")
                backoff_sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
            return resp.content.decode(encoding, errors="replace")
        except requests.RequestException as e:
            last_exc = e
            backoff_sleep(delay)
            delay *= 2
    raise RuntimeError(f"fetch failed: {url}") from last_exc
