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
