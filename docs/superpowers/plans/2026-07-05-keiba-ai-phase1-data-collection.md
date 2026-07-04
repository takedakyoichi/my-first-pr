# 競馬予想AI Phase 1（データ収集）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** netkeiba から JRA 中央競馬・直近5年の全レース（出馬表・確定着順・単勝オッズ・払戻）を、礼儀正しいスクレイピングでローカル SQLite（`race.db`）へ収集する。中断・再開でき、取得済みページは再取得しない。

**Architecture:** 責務ごとに薄いモジュールへ分割する。`fetcher`（HTTP取得＋スリープ＋キャッシュ＋バックオフ）→ `discovery`（開催日から race_id 一覧を発見）→ `parser`（キャッシュ済みHTMLをパースして構造化）→ `db`（SQLite スキーマとupsert）→ `ingest`（オーケストレーション＋進捗記録で再開可能）。各段の中間成果物（生HTML・DB）はファイルとして残す。パーサは保存した実HTMLフィクスチャに対して単体テストする。

**Tech Stack:** Python 3.11+, `requests`, `beautifulsoup4`, `lxml`, 標準ライブラリ `sqlite3`, `pytest`。

## Global Constraints

- 対象は **JRA 中央競馬のみ**、直近5年（実装時に開始日を確定。例: 2021-01-01 〜 2025-12-31）。
- **1リクエストごとに 2〜4 秒スリープ（ジッター付き）**。連続アクセスしない。
- **取得済みページはローカルにキャッシュ（`data/cache/`）し、再取得しない**。
- **中断・再開できる**（どの race_id まで処理したかを記録し、途中から再開）。
- User-Agent を明示。HTTP エラー / レート制限時は指数バックオフ。
- 取得データは**ローカル保持のみ**（個人の学習・検証目的）。
- db.netkeiba.com のページ文字コードは **EUC-JP**。デコードを誤ると文字化けするので必ず明示的に扱う。
- TDD（test-first）。各タスクは独立してテスト可能な成果物で終わる。パーサ系のテストは**保存した実HTMLフィクスチャ**に対して行う（ネットワークにアクセスしない）。
- コミットはタスクごと（各タスク末尾の Step でコミット）。

---

## File Structure

```
競馬予想アプリ/
  keiba/
    __init__.py
    config.py          # 定数（日付範囲・スリープ秒・パス・UA）
    fetcher.py         # HTTP取得＋キャッシュ＋スリープ＋バックオフ
    discovery.py       # 開催日→race_id一覧の発見
    parser.py          # HTML→構造化データ（レース/出走/払戻）
    db.py              # SQLiteスキーマ＋接続＋upsert
    ingest.py          # オーケストレーション＋進捗管理（再開可能）
  scripts/
    collect.py         # CLIエントリ（範囲指定で収集実行）
  data/
    cache/             # 生HTMLキャッシュ（.gitignore）
    race.db            # SQLite（.gitignore）
  tests/
    fixtures/          # 保存した実HTML（テスト用）
    test_db.py
    test_fetcher.py
    test_discovery.py
    test_parser.py
    test_ingest.py
  requirements.txt
  .gitignore
```

作業ディレクトリのルートは `競馬予想アプリ/`。以降のパスはこのディレクトリ基準。

---

### Task 1: プロジェクト雛形と DB スキーマ

**Files:**
- Create: `競馬予想アプリ/requirements.txt`
- Create: `競馬予想アプリ/.gitignore`
- Create: `競馬予想アプリ/keiba/__init__.py`
- Create: `競馬予想アプリ/keiba/config.py`
- Create: `競馬予想アプリ/keiba/db.py`
- Test: `競馬予想アプリ/tests/test_db.py`

**Interfaces:**
- Produces:
  - `keiba.config`: `DATA_DIR: Path`, `CACHE_DIR: Path`, `DB_PATH: Path`, `USER_AGENT: str`, `SLEEP_MIN: float`, `SLEEP_MAX: float`, `DATE_START: str`, `DATE_END: str`
  - `keiba.db.connect(db_path: Path) -> sqlite3.Connection`
  - `keiba.db.init_schema(conn: sqlite3.Connection) -> None`
  - `keiba.db.upsert_race(conn, race: dict) -> None`
  - `keiba.db.upsert_entries(conn, race_id: str, entries: list[dict]) -> None`
  - `keiba.db.upsert_payouts(conn, race_id: str, payouts: list[dict]) -> None`
  - `keiba.db.race_exists(conn, race_id: str) -> bool`

- [ ] **Step 1: requirements と .gitignore を作成**

`requirements.txt`:
```
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.0
pytest>=8.0
```

`.gitignore`:
```
data/cache/
data/race.db
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 2: config.py を作成**

```python
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
```

- [ ] **Step 3: 失敗するテストを書く（スキーマとupsert）**

`tests/test_db.py`:
```python
import sqlite3
from keiba import db


def make_conn():
    conn = sqlite3.connect(":memory:")
    db.init_schema(conn)
    return conn


def test_init_schema_creates_tables():
    conn = make_conn()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"races", "entries", "horses", "payouts", "ingest_progress"} <= names


def test_upsert_race_and_exists():
    conn = make_conn()
    assert db.race_exists(conn, "202105021211") is False
    db.upsert_race(conn, {
        "race_id": "202105021211", "date": "2021-05-30", "course": "東京",
        "distance": 2400, "surface": "芝", "going": "良", "race_class": "G1",
        "num_runners": 18, "weather": "晴",
    })
    assert db.race_exists(conn, "202105021211") is True
    # upsert は冪等（同じ race_id で重複行を作らない）
    db.upsert_race(conn, {
        "race_id": "202105021211", "date": "2021-05-30", "course": "東京",
        "distance": 2400, "surface": "芝", "going": "良", "race_class": "G1",
        "num_runners": 18, "weather": "晴",
    })
    n = conn.execute("SELECT COUNT(*) FROM races").fetchone()[0]
    assert n == 1


def test_upsert_entries_replaces():
    conn = make_conn()
    rows = [{
        "race_id": "202105021211", "horse_id": "2018105123", "horse_no": 1,
        "draw": 1, "jockey": "ルメール", "trainer": "友道", "sex_age": "牡3",
        "weight_carried": 57.0, "win_odds": 3.4, "popularity": 1,
        "finish_pos": 1, "time_sec": 145.2, "last_3f": 33.7, "margin": "",
    }]
    db.upsert_entries(conn, "202105021211", rows)
    db.upsert_entries(conn, "202105021211", rows)  # 再実行で重複しない
    n = conn.execute("SELECT COUNT(*) FROM entries WHERE race_id=?",
                     ("202105021211",)).fetchone()[0]
    assert n == 1


def test_upsert_payouts():
    conn = make_conn()
    pays = [
        {"bet_type": "win", "combination": "1", "payout": 340, "popularity": 1},
        {"bet_type": "wide", "combination": "1-5", "payout": 620, "popularity": 3},
    ]
    db.upsert_payouts(conn, "202105021211", pays)
    n = conn.execute("SELECT COUNT(*) FROM payouts WHERE race_id=?",
                     ("202105021211",)).fetchone()[0]
    assert n == 2
```

- [ ] **Step 4: テストを実行して失敗を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_db.py -v`
Expected: FAIL（`keiba.db` が無い / 関数未定義）

- [ ] **Step 5: db.py を実装**

```python
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    race_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    course TEXT, distance INTEGER, surface TEXT, going TEXT,
    race_class TEXT, num_runners INTEGER, weather TEXT
);
CREATE TABLE IF NOT EXISTS entries (
    race_id TEXT NOT NULL,
    horse_id TEXT, horse_no INTEGER, draw INTEGER,
    jockey TEXT, trainer TEXT, sex_age TEXT,
    weight_carried REAL, win_odds REAL, popularity INTEGER,
    finish_pos INTEGER, time_sec REAL, last_3f REAL, margin TEXT,
    PRIMARY KEY (race_id, horse_no)
);
CREATE TABLE IF NOT EXISTS horses (
    horse_id TEXT PRIMARY KEY,
    name TEXT
);
CREATE TABLE IF NOT EXISTS payouts (
    race_id TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    combination TEXT NOT NULL,
    payout INTEGER, popularity INTEGER,
    PRIMARY KEY (race_id, bet_type, combination)
);
CREATE TABLE IF NOT EXISTS ingest_progress (
    race_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,          -- 'done' | 'empty' | 'error'
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_races_date ON races(date);
CREATE INDEX IF NOT EXISTS idx_entries_race ON entries(race_id);
CREATE INDEX IF NOT EXISTS idx_entries_horse ON entries(horse_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def race_exists(conn, race_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM races WHERE race_id=?", (race_id,)).fetchone()
    return row is not None


def upsert_race(conn, race: dict) -> None:
    conn.execute(
        """INSERT INTO races
           (race_id, date, course, distance, surface, going, race_class, num_runners, weather)
           VALUES (:race_id, :date, :course, :distance, :surface, :going,
                   :race_class, :num_runners, :weather)
           ON CONFLICT(race_id) DO UPDATE SET
             date=excluded.date, course=excluded.course, distance=excluded.distance,
             surface=excluded.surface, going=excluded.going, race_class=excluded.race_class,
             num_runners=excluded.num_runners, weather=excluded.weather""",
        race,
    )
    conn.commit()


def upsert_entries(conn, race_id: str, entries: list[dict]) -> None:
    conn.execute("DELETE FROM entries WHERE race_id=?", (race_id,))
    conn.executemany(
        """INSERT INTO entries
           (race_id, horse_id, horse_no, draw, jockey, trainer, sex_age,
            weight_carried, win_odds, popularity, finish_pos, time_sec, last_3f, margin)
           VALUES (:race_id, :horse_id, :horse_no, :draw, :jockey, :trainer, :sex_age,
                   :weight_carried, :win_odds, :popularity, :finish_pos, :time_sec,
                   :last_3f, :margin)""",
        [{"race_id": race_id, **e} for e in entries],
    )
    conn.commit()


def upsert_payouts(conn, race_id: str, payouts: list[dict]) -> None:
    conn.execute("DELETE FROM payouts WHERE race_id=?", (race_id,))
    conn.executemany(
        """INSERT INTO payouts (race_id, bet_type, combination, payout, popularity)
           VALUES (:race_id, :bet_type, :combination, :payout, :popularity)""",
        [{"race_id": race_id, **p} for p in payouts],
    )
    conn.commit()


def mark_progress(conn, race_id: str, status: str) -> None:
    from datetime import datetime, timezone
    conn.execute(
        """INSERT INTO ingest_progress (race_id, status, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(race_id) DO UPDATE SET status=excluded.status,
             updated_at=excluded.updated_at""",
        (race_id, status, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def processed_race_ids(conn) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT race_id FROM ingest_progress WHERE status IN ('done','empty')"
    )}
```

- [ ] **Step 6: テストを実行して成功を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_db.py -v`
Expected: PASS（4件）

- [ ] **Step 7: コミット**

```bash
cd 競馬予想アプリ && git add requirements.txt .gitignore keiba/__init__.py keiba/config.py keiba/db.py tests/test_db.py
git commit -m "feat(keiba): project scaffold and SQLite schema"
```

---

### Task 2: 礼儀正しい HTTP フェッチャ（キャッシュ＋スリープ＋バックオフ）

**Files:**
- Create: `競馬予想アプリ/keiba/fetcher.py`
- Test: `競馬予想アプリ/tests/test_fetcher.py`

**Interfaces:**
- Consumes: `keiba.config`（`CACHE_DIR`, `USER_AGENT`, `SLEEP_MIN/MAX`）
- Produces:
  - `keiba.fetcher.cache_path(url: str) -> Path`（URLのSHA1でキャッシュファイル名を決める）
  - `keiba.fetcher.fetch(url, *, encoding="euc-jp", session=None, sleeper=None, max_retries=3) -> str`
    - キャッシュがあれば読み、無ければHTTP取得→キャッシュ保存→デコード済み文字列を返す
    - 取得時のみ `sleeper()` を呼ぶ（キャッシュヒット時は呼ばない）
    - 5xx/429 は指数バックオフで `max_retries` 回まで再試行

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_fetcher.py`:
```python
from pathlib import Path
from keiba import fetcher


class FakeResp:
    def __init__(self, content: bytes, status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, headers=None, timeout=None):
        self.calls += 1
        return self._responses.pop(0)


def test_fetch_writes_cache_and_decodes(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    body = "テスト".encode("euc-jp")
    sess = FakeSession([FakeResp(body)])
    sleeps = []
    out = fetcher.fetch("https://example.com/a", session=sess,
                        sleeper=lambda: sleeps.append(1))
    assert "テスト" in out
    assert sess.calls == 1
    assert len(sleeps) == 1                      # 取得時にスリープした
    assert fetcher.cache_path("https://example.com/a").exists()


def test_fetch_uses_cache_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    body = "あ".encode("euc-jp")
    sess = FakeSession([FakeResp(body)])
    sleeps = []
    fetcher.fetch("https://example.com/b", session=sess, sleeper=lambda: sleeps.append(1))
    out2 = fetcher.fetch("https://example.com/b", session=sess, sleeper=lambda: sleeps.append(1))
    assert out2 == "あ"
    assert sess.calls == 1                        # 2回目はHTTPを呼ばない
    assert len(sleeps) == 1                        # 2回目はスリープしない


def test_fetch_retries_on_5xx(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    body = "x".encode("euc-jp")
    sess = FakeSession([FakeResp(b"", 503), FakeResp(body, 200)])
    out = fetcher.fetch("https://example.com/c", session=sess,
                        sleeper=lambda: None, max_retries=3)
    assert out == "x"
    assert sess.calls == 2
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_fetcher.py -v`
Expected: FAIL（`keiba.fetcher` が無い）

- [ ] **Step 3: fetcher.py を実装**

```python
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


def fetch(url, *, encoding="euc-jp", session=None, sleeper=None, max_retries=3) -> str:
    path = cache_path(url)
    if path.exists():
        return path.read_bytes().decode(encoding, errors="replace")

    sess = session or requests.Session()
    sleeper = sleeper or _default_sleeper
    headers = {"User-Agent": config.USER_AGENT}

    delay = 1.0
    last_exc = None
    for attempt in range(max_retries):
        sleeper()  # 取得の前に必ず待つ（礼儀）
        try:
            resp = sess.get(url, headers=headers, timeout=30)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exc = RuntimeError(f"status {resp.status_code}")
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
            return resp.content.decode(encoding, errors="replace")
        except requests.RequestException as e:
            last_exc = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"fetch failed: {url}") from last_exc
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_fetcher.py -v`
Expected: PASS（3件）

- [ ] **Step 5: コミット**

```bash
cd 競馬予想アプリ && git add keiba/fetcher.py tests/test_fetcher.py
git commit -m "feat(keiba): polite HTTP fetcher with cache and backoff"
```

---

### Task 3: 実HTMLフィクスチャの取得（手動・1回だけ）

このタスクだけは「本物のHTMLを1件だけ取得して保存する」準備作業。以降のパーサ実装（Task 4）とdiscovery（Task 5）は、このフィクスチャに対してテストする。**ネットワークにアクセスする唯一の手作業**なので、礼儀正しく1〜2件だけ取得する。

**Files:**
- Create: `競馬予想アプリ/tests/fixtures/race_result_sample.html`（実取得して保存）
- Create: `競馬予想アプリ/tests/fixtures/race_list_sample.html`（実取得して保存）
- Create: `競馬予想アプリ/scripts/save_fixture.py`

**Interfaces:**
- Produces: `tests/fixtures/race_result_sample.html`（db.netkeiba.com のレース結果ページ1件）、`tests/fixtures/race_list_sample.html`（開催日のレース一覧ページ1件）

- [ ] **Step 1: フィクスチャ取得スクリプトを書く**

`scripts/save_fixture.py`:
```python
"""実HTMLを1件だけ取得してフィクスチャ保存する（手動実行）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from keiba import fetcher

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
FIX.mkdir(parents=True, exist_ok=True)

# 過去の実在レース（例）。存在する race_id に差し替えて実行する。
RACE_URL = "https://db.netkeiba.com/race/202105021211/"
# 開催日一覧（例）。実在の開催日に差し替える。
LIST_URL = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=20211226"

(FIX / "race_result_sample.html").write_text(fetcher.fetch(RACE_URL), encoding="utf-8")
(FIX / "race_list_sample.html").write_text(
    fetcher.fetch(LIST_URL, encoding="euc-jp"), encoding="utf-8")
print("saved fixtures")
```

- [ ] **Step 2: スクリプトを実行してフィクスチャを保存**

Run: `cd 競馬予想アプリ && python scripts/save_fixture.py`
Expected: `saved fixtures` と表示され、`tests/fixtures/` に2つのHTMLができる。
（もし race_id が404なら、netkeiba で実在する過去レースのURLに差し替えて再実行。取得は数件までに留める。）

- [ ] **Step 3: フィクスチャの中身を確認（パーサ実装の前提を掴む）**

Run: `cd 競馬予想アプリ && python -c "print(open('tests/fixtures/race_result_sample.html').read()[:2000])"`
Expected: レース結果テーブル（着順・馬番・騎手・単勝・人気 等）を含むHTMLが見える。
**このHTMLの実際のクラス名・列順を確認し、Task 4 のセレクタを現物に合わせて調整すること。** 以下のTask 4のコードは netkeiba の一般的な構造（結果テーブル `race_table_01`、払戻 `pay_table_01`、レース情報 `data_intro`）を前提にした初期値。

- [ ] **Step 4: コミット**

```bash
cd 競馬予想アプリ && git add scripts/save_fixture.py tests/fixtures/race_result_sample.html tests/fixtures/race_list_sample.html
git commit -m "chore(keiba): add real HTML fixtures for parser tests"
```

---

### Task 4: レース結果パーサ（フィクスチャに対してテスト）

**Files:**
- Create: `競馬予想アプリ/keiba/parser.py`
- Test: `競馬予想アプリ/tests/test_parser.py`

**Interfaces:**
- Consumes: `tests/fixtures/race_result_sample.html`
- Produces:
  - `keiba.parser.parse_race_result(html: str, race_id: str) -> dict`
    戻り値: `{"race": {...races列...}, "entries": [ {...entries列...} ], "payouts": [ {...payouts列...} ]}`
    - `race` は `upsert_race` が受け取る dict、`entries` は各要素が `upsert_entries` の要素、`payouts` は `upsert_payouts` の要素と同じキー。
    - パースできない/データ無しなら `entries` を空リストで返す（呼び出し側が 'empty' 判定できる）。

- [ ] **Step 1: 失敗するテストを書く（フィクスチャに対して）**

`tests/test_parser.py`:
```python
from pathlib import Path
from keiba import parser

FIX = Path(__file__).resolve().parent / "fixtures"


def load(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_parse_race_result_basic():
    html = load("race_result_sample.html")
    out = parser.parse_race_result(html, "202105021211")

    race = out["race"]
    assert race["race_id"] == "202105021211"
    assert race["distance"] and race["distance"] > 0          # 距離が数値
    assert race["surface"] in ("芝", "ダート")
    assert race["num_runners"] == len(out["entries"])

    entries = out["entries"]
    assert len(entries) > 0
    first = entries[0]
    # 必須フィールドが取れている
    for key in ("horse_no", "finish_pos", "jockey", "win_odds"):
        assert key in first
    # 着順は 1..num_runners の範囲（失格等の欠損は None 許容）
    positions = [e["finish_pos"] for e in entries if e["finish_pos"] is not None]
    assert min(positions) == 1

    payouts = out["payouts"]
    bet_types = {p["bet_type"] for p in payouts}
    assert "win" in bet_types            # 単勝の払戻がある
    # ワイドは存在すれば wide として取れている（無いレースもあるので緩め）
    for p in payouts:
        assert isinstance(p["payout"], int)
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_parser.py -v`
Expected: FAIL（`keiba.parser` が無い）

- [ ] **Step 3: parser.py を実装**

> **重要:** 以下は netkeiba の一般的なDOM構造を前提とした初期実装。**Task 3 で保存した実HTMLの実際のクラス名・列順を見て、セレクタと列インデックスを現物に合わせて修正すること。** テスト（フィクスチャ）が通れば正しく合っている。

```python
import re
from bs4 import BeautifulSoup


def _to_float(s):
    try:
        return float(str(s).strip())
    except (ValueError, AttributeError):
        return None


def _to_int(s):
    m = re.search(r"-?\d+", str(s))
    return int(m.group()) if m else None


def _time_to_sec(s):
    s = str(s).strip()
    m = re.match(r"(\d+):(\d+)\.(\d+)", s)      # 例 2:24.3
    if m:
        return int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 10
    return _to_float(s)


def parse_race_result(html: str, race_id: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    # --- レース情報（距離・馬場・馬場状態・天候・クラス） ---
    intro = soup.select_one("diary_snap_cut, .data_intro, .racedata")
    intro_text = (intro.get_text(" ", strip=True) if intro else soup.get_text(" ", strip=True))
    dist_m = re.search(r"(芝|ダ|ダート)(\d{3,4})m", intro_text)
    surface = None
    distance = None
    if dist_m:
        surface = "芝" if dist_m.group(1) == "芝" else "ダート"
        distance = int(dist_m.group(2))
    going_m = re.search(r"(良|稍重|重|不良)", intro_text)
    weather_m = re.search(r"(晴|曇|雨|小雨|雪|小雪)", intro_text)
    date_m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", intro_text)
    date = None
    if date_m:
        date = f"{date_m.group(1)}-{int(date_m.group(2)):02d}-{int(date_m.group(3)):02d}"
    class_m = re.search(r"\b(G[123]|オープン|OP|\d+勝クラス|新馬|未勝利)\b", intro_text)

    # --- 出走馬テーブル ---
    table = soup.select_one("table.race_table_01") or soup.select_one("table[summary*='レース']")
    entries = []
    if table:
        rows = table.select("tr")[1:]           # 先頭はヘッダ
        for tr in rows:
            tds = tr.select("td")
            if len(tds) < 12:
                continue
            # 列インデックスは実HTMLに合わせて調整（初期値は一般的な並び）
            finish_pos = _to_int(tds[0].get_text())
            horse_no = _to_int(tds[2].get_text())
            horse_link = tds[3].select_one("a[href*='/horse/']")
            horse_id = None
            if horse_link:
                hm = re.search(r"/horse/(\w+)", horse_link.get("href", ""))
                horse_id = hm.group(1) if hm else None
            sex_age = tds[4].get_text(strip=True)
            weight_carried = _to_float(tds[5].get_text())
            jockey = tds[6].get_text(strip=True)
            time_sec = _time_to_sec(tds[7].get_text())
            margin = tds[8].get_text(strip=True)
            last_3f = _to_float(tds[11].get_text())
            win_odds = None
            popularity = None
            for td in tds:
                t = td.get_text(strip=True)
                if re.fullmatch(r"\d+\.\d", t) and win_odds is None:
                    win_odds = float(t)
            trainer_link = tr.select_one("a[href*='/trainer/']")
            trainer = trainer_link.get_text(strip=True) if trainer_link else ""
            draw = None
            entries.append({
                "horse_id": horse_id, "horse_no": horse_no, "draw": draw,
                "jockey": jockey, "trainer": trainer, "sex_age": sex_age,
                "weight_carried": weight_carried, "win_odds": win_odds,
                "popularity": popularity, "finish_pos": finish_pos,
                "time_sec": time_sec, "last_3f": last_3f, "margin": margin,
            })

    # --- 払戻（単勝・ワイド） ---
    payouts = []
    for ptable in soup.select("table.pay_table_01"):
        for tr in ptable.select("tr"):
            th = tr.select_one("th")
            tds = tr.select("td")
            if not th or len(tds) < 2:
                continue
            label = th.get_text(strip=True)
            bet_type = None
            if "単勝" in label:
                bet_type = "win"
            elif "ワイド" in label:
                bet_type = "wide"
            if bet_type is None:
                continue
            combos = [x for x in tds[0].get_text("\n").split("\n") if x.strip()]
            pays = re.findall(r"[\d,]+", tds[1].get_text("\n"))
            pops = re.findall(r"\d+", tds[2].get_text("\n")) if len(tds) > 2 else []
            for i, combo in enumerate(combos):
                if i >= len(pays):
                    break
                payouts.append({
                    "bet_type": bet_type,
                    "combination": combo.replace(" ", ""),
                    "payout": int(pays[i].replace(",", "")),
                    "popularity": int(pops[i]) if i < len(pops) else None,
                })

    race = {
        "race_id": race_id, "date": date, "course": None,
        "distance": distance, "surface": surface,
        "going": going_m.group(1) if going_m else None,
        "race_class": class_m.group(1) if class_m else None,
        "num_runners": len(entries),
        "weather": weather_m.group(1) if weather_m else None,
    }
    return {"race": race, "entries": entries, "payouts": payouts}
```

- [ ] **Step 4: テストを実行して成功を確認（現物に合わせて調整しながら）**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_parser.py -v`
Expected: PASS。落ちる場合はフィクスチャHTMLの実際の列順・クラス名を見てセレクタ/インデックスを直す（これがこのタスクの本体作業）。

- [ ] **Step 5: コミット**

```bash
cd 競馬予想アプリ && git add keiba/parser.py tests/test_parser.py
git commit -m "feat(keiba): parse race result (entries + payouts) from HTML"
```

---

### Task 5: 開催日→race_id 発見（discovery）

**Files:**
- Create: `競馬予想アプリ/keiba/discovery.py`
- Test: `競馬予想アプリ/tests/test_discovery.py`

**Interfaces:**
- Consumes: `keiba.fetcher.fetch`、`tests/fixtures/race_list_sample.html`
- Produces:
  - `keiba.discovery.parse_race_ids(list_html: str) -> list[str]`（一覧ページHTMLから race_id を抽出）
  - `keiba.discovery.jra_race_dates(start: str, end: str) -> list[str]`（期間内の土日祝の候補日を `YYYYMMDD` で返す。実際に開催が無い日は一覧ページが空になるだけなので許容）
  - `keiba.discovery.race_ids_for_date(date_yyyymmdd: str, fetch=fetcher.fetch) -> list[str]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_discovery.py`:
```python
from pathlib import Path
from keiba import discovery

FIX = Path(__file__).resolve().parent / "fixtures"


def test_parse_race_ids_from_fixture():
    html = (FIX / "race_list_sample.html").read_text(encoding="utf-8")
    ids = discovery.parse_race_ids(html)
    assert len(ids) > 0
    # netkeiba の race_id は12桁数字
    assert all(len(i) == 12 and i.isdigit() for i in ids)


def test_jra_race_dates_are_weekend_or_holiday():
    dates = discovery.jra_race_dates("2021-12-25", "2021-12-27")
    # 12/25(土),12/26(日) を含み、12/27(月)は含まない
    assert "20211225" in dates
    assert "20211226" in dates
    assert "20211227" not in dates


def test_race_ids_for_date_uses_fetch():
    html = (FIX / "race_list_sample.html").read_text(encoding="utf-8")
    ids = discovery.race_ids_for_date("20211226", fetch=lambda url, **k: html)
    assert len(ids) > 0
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_discovery.py -v`
Expected: FAIL（`keiba.discovery` が無い）

- [ ] **Step 3: discovery.py を実装**

> race_id 抽出の正規表現は、フィクスチャの実際のリンク形式に合わせて調整すること。

```python
import re
from datetime import date, timedelta

from keiba import fetcher

LIST_URL = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date}"


def parse_race_ids(list_html: str) -> list[str]:
    # 一覧ページ内の race_id=123456789012 または /race/shutuba... のリンクから抽出
    ids = set(re.findall(r"race_id=(\d{12})", list_html))
    if not ids:
        ids = set(re.findall(r"/race/(\d{12})", list_html))
    return sorted(ids)


def jra_race_dates(start: str, end: str) -> list[str]:
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    out = []
    d = d0
    while d <= d1:
        if d.weekday() >= 5:               # 土(5)・日(6)。祝日開催は一覧が空なら自然にスキップ
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def race_ids_for_date(date_yyyymmdd: str, fetch=fetcher.fetch) -> list[str]:
    html = fetch(LIST_URL.format(date=date_yyyymmdd), encoding="euc-jp")
    return parse_race_ids(html)
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_discovery.py -v`
Expected: PASS（3件）。`test_parse_race_ids_from_fixture` が落ちる場合はフィクスチャの実リンク形式に正規表現を合わせる。

- [ ] **Step 5: コミット**

```bash
cd 競馬予想アプリ && git add keiba/discovery.py tests/test_discovery.py
git commit -m "feat(keiba): discover race_ids from kaisai date list"
```

---

### Task 6: 収集オーケストレーション（再開可能）＋ CLI

**Files:**
- Create: `競馬予想アプリ/keiba/ingest.py`
- Create: `競馬予想アプリ/scripts/collect.py`
- Test: `競馬予想アプリ/tests/test_ingest.py`

**Interfaces:**
- Consumes: `keiba.db`, `keiba.parser.parse_race_result`, `keiba.discovery`, `keiba.fetcher`
- Produces:
  - `keiba.ingest.ingest_race(conn, race_id, *, fetch, parse) -> str`（'done'|'empty'）。既に処理済みならフェッチせず 'skip' を返す。
  - `keiba.ingest.run(conn, date_start, date_end, *, fetch=fetcher.fetch) -> dict`（集計 `{"done": n, "empty": n, "skip": n}` を返す）
  - RESULT_URL = `https://db.netkeiba.com/race/{race_id}/`

- [ ] **Step 1: 失敗するテストを書く（ネットワーク無し・スタブで）**

`tests/test_ingest.py`:
```python
import sqlite3
from keiba import db, ingest


def make_conn():
    conn = sqlite3.connect(":memory:")
    db.init_schema(conn)
    return conn


def fake_parse_full(html, race_id):
    return {
        "race": {"race_id": race_id, "date": "2021-12-26", "course": None,
                 "distance": 1600, "surface": "芝", "going": "良",
                 "race_class": "G1", "num_runners": 2, "weather": "晴"},
        "entries": [
            {"horse_id": "h1", "horse_no": 1, "draw": 1, "jockey": "A",
             "trainer": "T", "sex_age": "牡3", "weight_carried": 55.0,
             "win_odds": 2.1, "popularity": 1, "finish_pos": 1,
             "time_sec": 95.0, "last_3f": 33.5, "margin": ""},
            {"horse_id": "h2", "horse_no": 2, "draw": 2, "jockey": "B",
             "trainer": "T2", "sex_age": "牝4", "weight_carried": 55.0,
             "win_odds": 5.0, "popularity": 2, "finish_pos": 2,
             "time_sec": 95.2, "last_3f": 33.9, "margin": "1"},
        ],
        "payouts": [{"bet_type": "win", "combination": "1", "payout": 210,
                     "popularity": 1}],
    }


def fake_parse_empty(html, race_id):
    return {"race": {"race_id": race_id, "date": None, "course": None,
                     "distance": None, "surface": None, "going": None,
                     "race_class": None, "num_runners": 0, "weather": None},
            "entries": [], "payouts": []}


def test_ingest_race_done_writes_rows():
    conn = make_conn()
    status = ingest.ingest_race(conn, "202112260111",
                                fetch=lambda url, **k: "<html>", parse=fake_parse_full)
    assert status == "done"
    assert db.race_exists(conn, "202112260111")
    n = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert n == 2


def test_ingest_race_empty():
    conn = make_conn()
    status = ingest.ingest_race(conn, "999999999999",
                                fetch=lambda url, **k: "<html>", parse=fake_parse_empty)
    assert status == "empty"


def test_ingest_race_skips_processed():
    conn = make_conn()
    calls = {"n": 0}

    def counting_fetch(url, **k):
        calls["n"] += 1
        return "<html>"

    ingest.ingest_race(conn, "202112260111", fetch=counting_fetch, parse=fake_parse_full)
    status = ingest.ingest_race(conn, "202112260111", fetch=counting_fetch, parse=fake_parse_full)
    assert status == "skip"
    assert calls["n"] == 1        # 2回目はfetchしない（再開可能・再取得しない）


def test_run_aggregates(monkeypatch):
    conn = make_conn()
    monkeypatch.setattr(ingest.discovery, "jra_race_dates", lambda s, e: ["20211226"])
    monkeypatch.setattr(ingest.discovery, "race_ids_for_date",
                        lambda d, fetch=None: ["202112260111", "999999999999"])

    def route_parse(html, race_id):
        return fake_parse_full(html, race_id) if race_id.endswith("0111") else fake_parse_empty(html, race_id)

    summary = ingest.run(conn, "2021-12-26", "2021-12-26",
                         fetch=lambda url, **k: "<html>", parse=route_parse)
    assert summary["done"] == 1
    assert summary["empty"] == 1
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_ingest.py -v`
Expected: FAIL（`keiba.ingest` が無い）

- [ ] **Step 3: ingest.py を実装**

```python
from keiba import db, discovery, fetcher, parser

RESULT_URL = "https://db.netkeiba.com/race/{race_id}/"


def ingest_race(conn, race_id, *, fetch=fetcher.fetch, parse=parser.parse_race_result) -> str:
    if race_id in db.processed_race_ids(conn):
        return "skip"
    html = fetch(RESULT_URL.format(race_id=race_id))
    parsed = parse(html, race_id)
    if not parsed["entries"]:
        db.mark_progress(conn, race_id, "empty")
        return "empty"
    db.upsert_race(conn, parsed["race"])
    db.upsert_entries(conn, race_id, parsed["entries"])
    db.upsert_payouts(conn, race_id, parsed["payouts"])
    db.mark_progress(conn, race_id, "done")
    return "done"


def run(conn, date_start, date_end, *, fetch=fetcher.fetch,
        parse=parser.parse_race_result) -> dict:
    summary = {"done": 0, "empty": 0, "skip": 0}
    for d in discovery.jra_race_dates(date_start, date_end):
        for race_id in discovery.race_ids_for_date(d, fetch=fetch):
            status = ingest_race(conn, race_id, fetch=fetch, parse=parse)
            summary[status] = summary.get(status, 0) + 1
    return summary
```

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd 競馬予想アプリ && python -m pytest tests/test_ingest.py -v`
Expected: PASS（4件）

- [ ] **Step 5: CLI エントリを実装**

`scripts/collect.py`:
```python
"""収集CLI: 期間を指定して race.db に収集する。中断しても再実行で続きから。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from keiba import config, db, ingest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=config.DATE_START)
    ap.add_argument("--end", default=config.DATE_END)
    args = ap.parse_args()

    conn = db.connect(config.DB_PATH)
    db.init_schema(conn)
    print(f"collecting {args.start} .. {args.end} -> {config.DB_PATH}")
    summary = ingest.run(conn, args.start, args.end)
    print("summary:", summary)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 小さな範囲で実データ疎通（1開催日だけ）**

Run: `cd 競馬予想アプリ && python scripts/collect.py --start 2021-12-26 --end 2021-12-26`
Expected: `summary: {'done': N, ...}` と表示され、`data/race.db` にレコードが入る。
確認: `cd 競馬予想アプリ && python -c "import sqlite3;c=sqlite3.connect('data/race.db');print('races',c.execute('SELECT COUNT(*) FROM races').fetchone()[0]);print('entries',c.execute('SELECT COUNT(*) FROM entries').fetchone()[0])"`
Expected: races と entries が正の数。
（この実行はネットワークアクセスするので、礼儀正しいスリープが効いていること・キャッシュができていることを確認。2回目実行が 'skip' 中心になればOK。）

- [ ] **Step 7: コミット**

```bash
cd 競馬予想アプリ && git add keiba/ingest.py scripts/collect.py tests/test_ingest.py
git commit -m "feat(keiba): resumable ingestion orchestrator and collect CLI"
```

---

### Task 7: 本収集（5年ぶん）と健全性チェック

**Files:**
- Create: `競馬予想アプリ/scripts/db_stats.py`
- Test: なし（運用タスク。健全性はスクリプトで確認）

**Interfaces:**
- Consumes: `keiba.db`, `config.DB_PATH`
- Produces: DB統計の標準出力

- [ ] **Step 1: 統計スクリプトを書く**

`scripts/db_stats.py`:
```python
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from keiba import config

c = sqlite3.connect(config.DB_PATH)
print("races:", c.execute("SELECT COUNT(*) FROM races").fetchone()[0])
print("entries:", c.execute("SELECT COUNT(*) FROM entries").fetchone()[0])
print("date range:", c.execute("SELECT MIN(date), MAX(date) FROM races").fetchone())
print("win payouts:", c.execute("SELECT COUNT(*) FROM payouts WHERE bet_type='win'").fetchone()[0])
print("wide payouts:", c.execute("SELECT COUNT(*) FROM payouts WHERE bet_type='wide'").fetchone()[0])
# 健全性: finish_pos が全滅していないか
print("entries with finish_pos:", c.execute(
    "SELECT COUNT(*) FROM entries WHERE finish_pos IS NOT NULL").fetchone()[0])
print("entries with win_odds:", c.execute(
    "SELECT COUNT(*) FROM entries WHERE win_odds IS NOT NULL").fetchone()[0])
```

- [ ] **Step 2: 本収集を分割実行（中断・再開しながら）**

5年ぶんは数万レース。1年ずつ回すのを推奨（各回はネットワークアクセスし、スリープが入るため長時間）。
Run（例、1年ずつ）:
```bash
cd 競馬予想アプリ
python scripts/collect.py --start 2021-01-01 --end 2021-12-31
python scripts/collect.py --start 2022-01-01 --end 2022-12-31
python scripts/collect.py --start 2023-01-01 --end 2023-12-31
python scripts/collect.py --start 2024-01-01 --end 2024-12-31
python scripts/collect.py --start 2025-01-01 --end 2025-12-31
```
Expected: 各実行が `summary` を出す。途中で止めても、再実行すれば `skip` で続きから進む。

- [ ] **Step 3: 健全性チェック**

Run: `cd 競馬予想アプリ && python scripts/db_stats.py`
Expected:
- races が数千〜1万超（5年ぶん）
- date range が 2021〜2025 を概ねカバー
- win payouts ≈ races 数、wide payouts も相当数
- entries with finish_pos / win_odds が entries 総数に近い（欠損が大量でない）
欠損が大量なら Task 4 のパーサを実HTMLに合わせて修正し、該当 race の `ingest_progress` を消して再収集する。

- [ ] **Step 4: コミット**

```bash
cd 競馬予想アプリ && git add scripts/db_stats.py
git commit -m "chore(keiba): add DB health-check stats script"
```

---

## Self-Review

**Spec coverage（対 検証MVPスペック §3 データ収集）:**
- JRA中央・直近5年 → Task 6/7（`--start/--end`, `jra_race_dates`）✓
- 出馬表・確定着順・単勝オッズ・払戻（単勝/ワイド） → Task 4 パーサ（entries に finish_pos/win_odds、payouts に win/wide）✓
- スリープ（2〜4秒ジッター） → Task 2 `_default_sleeper` / `SLEEP_MIN/MAX` ✓
- 取得済みキャッシュして再取得しない → Task 2 `cache_path`/キャッシュ分岐 ✓
- 中断・再開できる → Task 1 `ingest_progress` + Task 6 `processed_race_ids`/'skip' ✓
- DBスキーマ（races/entries/horses/payouts） → Task 1 ✓
- パーサをキャッシュHTMLに対してテスト → Task 3 フィクスチャ + Task 4/5 テスト ✓
- EUC-JP デコード → Task 2 `fetch(encoding="euc-jp")` ✓
- 日付ベース追記・時系列再実行可能（継続学習の布石, スペック§8） → 日付キーの upsert と冪等 ingest で満たす ✓
- （horses テーブルは本フェーズでは name 未投入。馬名は Phase 2/3 で馬ページ収集時に補完する想定。スキーマは用意済み。）

**Placeholder scan:** 「実HTMLに合わせて調整」は具体作業（フィクスチャに対しテストが通ること）を伴う指示であり、プレースホルダではない。TODO/TBD 無し。✓

**Type consistency:** `parse_race_result` の戻り値キー（race/entries/payouts）は `upsert_*` の引数キーと一致。`ingest_race` の返り値 'done'/'empty'/'skip' は `run` の集計・テストと一致。`fetch`/`parse` の注入シグネチャはテストのスタブと一致。✓

---

## 次の計画（この計画の完了後）

**計画B = Phase 2（特徴量→LightGBM→回収率backtest）** を別途 writing-plans で作成する。前提: 本計画で `race.db` に5年ぶんのデータが入り、`db_stats.py` の健全性チェックが通っていること。
