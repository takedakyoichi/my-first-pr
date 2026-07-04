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


_ENTRY_COLUMNS = (
    "horse_id", "horse_no", "draw", "jockey", "trainer", "sex_age",
    "weight_carried", "win_odds", "popularity", "finish_pos", "time_sec",
    "last_3f", "margin",
)


def upsert_entries(conn, race_id: str, entries: list[dict]) -> None:
    conn.execute("DELETE FROM entries WHERE race_id=?", (race_id,))
    conn.executemany(
        """INSERT INTO entries
           (race_id, horse_id, horse_no, draw, jockey, trainer, sex_age,
            weight_carried, win_odds, popularity, finish_pos, time_sec, last_3f, margin)
           VALUES (:race_id, :horse_id, :horse_no, :draw, :jockey, :trainer, :sex_age,
                   :weight_carried, :win_odds, :popularity, :finish_pos, :time_sec,
                   :last_3f, :margin)""",
        # Select only the columns this INSERT needs -- entry dicts may carry
        # extra keys (e.g. "horse_name", used only for upsert_horses) that
        # must not break this named-parameter query.
        [{"race_id": race_id, **{c: e.get(c) for c in _ENTRY_COLUMNS}} for e in entries],
    )
    conn.commit()


def upsert_horses(conn, horses: list[dict]) -> None:
    rows = [h for h in horses if h.get("horse_id")]
    if not rows:
        return
    conn.executemany(
        """INSERT INTO horses (horse_id, name)
           VALUES (:horse_id, :name)
           ON CONFLICT(horse_id) DO UPDATE SET name=excluded.name""",
        rows,
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
