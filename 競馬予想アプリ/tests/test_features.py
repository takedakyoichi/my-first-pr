import sqlite3

import numpy as np
import pandas as pd

from keiba import db, features


def make_conn():
    conn = sqlite3.connect(":memory:")
    db.init_schema(conn)
    return conn


def add_race(conn, race_id, date, **overrides):
    race = {
        "race_id": race_id, "date": date, "course": "東京",
        "distance": 2000, "surface": "芝", "going": "良",
        "race_class": "G3", "num_runners": 4, "weather": "晴",
    }
    race.update(overrides)
    db.upsert_race(conn, race)


def add_entries(conn, race_id, rows):
    # rows: list of dicts with at least horse_no; fill defaults for the rest.
    defaults = {
        "draw": None, "jockey": None, "trainer": None, "sex_age": "牡3",
        "weight_carried": 55.0, "win_odds": 5.0, "popularity": 1,
        "finish_pos": None, "time_sec": None, "last_3f": None, "margin": "",
    }
    full_rows = []
    for r in rows:
        row = dict(defaults)
        row.update(r)
        row.setdefault("horse_id", f"h{r['horse_no']}")
        full_rows.append(row)
    db.upsert_entries(conn, race_id, full_rows)


def build_basic_dataset():
    """3 races across 3 dates, 2 jockeys, some horse history, one scratch."""
    conn = make_conn()

    # Race 1: 2024-01-01. Jockey A wins on horse h1. Jockey B loses on h2.
    add_race(conn, "R1", "2024-01-01", num_runners=3)
    add_entries(conn, "R1", [
        {"horse_no": 1, "horse_id": "h1", "draw": 1, "jockey": "A", "trainer": "TA",
         "sex_age": "牡3", "finish_pos": 1, "last_3f": 34.0, "win_odds": 3.0, "popularity": 1},
        {"horse_no": 2, "horse_id": "h2", "draw": 2, "jockey": "B", "trainer": "TB",
         "sex_age": "牝4", "finish_pos": 2, "last_3f": 34.5, "win_odds": 5.0, "popularity": 2},
        {"horse_no": 3, "horse_id": "h3", "draw": 3, "jockey": "B", "trainer": "TB",
         "sex_age": "セ5", "finish_pos": None, "last_3f": None, "win_odds": 20.0, "popularity": 3},
    ])

    # Race 2: 2024-01-08. Jockey A loses on h1 (his 2nd ride). Jockey B wins on h2.
    add_race(conn, "R2", "2024-01-08", num_runners=3)
    add_entries(conn, "R2", [
        {"horse_no": 1, "horse_id": "h1", "draw": 2, "jockey": "A", "trainer": "TA",
         "sex_age": "牡3", "finish_pos": 3, "last_3f": 35.0, "win_odds": 4.0, "popularity": 2},
        {"horse_no": 2, "horse_id": "h2", "draw": 1, "jockey": "B", "trainer": "TB",
         "sex_age": "牝4", "finish_pos": 1, "last_3f": 33.5, "win_odds": 2.5, "popularity": 1},
        {"horse_no": 3, "horse_id": "h4", "draw": 3, "jockey": "A", "trainer": "TA",
         "sex_age": "牡4", "finish_pos": 2, "last_3f": 34.2, "win_odds": 6.0, "popularity": 3},
    ])

    # Race 3: 2024-01-15. Jockey A wins again on h1 (his 3rd ride).
    add_race(conn, "R3", "2024-01-15", num_runners=2)
    add_entries(conn, "R3", [
        {"horse_no": 1, "horse_id": "h1", "draw": 1, "jockey": "A", "trainer": "TA",
         "sex_age": "牡3", "finish_pos": 1, "last_3f": 33.8, "win_odds": 2.0, "popularity": 1},
        {"horse_no": 2, "horse_id": "h5", "draw": 2, "jockey": "C", "trainer": "TC",
         "sex_age": "牝3", "finish_pos": 2, "last_3f": 34.9, "win_odds": 8.0, "popularity": 2},
    ])

    return conn


def test_y_win_is_1_only_for_finish_pos_1_and_scratched_are_0():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    r1 = df[df["race_id"] == "R1"].set_index("horse_no")
    assert r1.loc[1, "y_win"] == 1  # h1 finished 1st
    assert r1.loc[2, "y_win"] == 0  # h2 finished 2nd
    assert r1.loc[3, "y_win"] == 0  # scratched (finish_pos NULL)
    assert r1.loc[3, "y_top3"] == 0


def test_y_top3_is_1_for_finish_pos_1_to_3():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    r2 = df[df["race_id"] == "R2"].set_index("horse_no")
    assert r2.loc[1, "y_top3"] == 1  # finished 3rd
    assert r2.loc[2, "y_top3"] == 1  # finished 1st
    assert r2.loc[3, "y_top3"] == 1  # finished 2nd


def test_jockey_win_rate_excludes_future_races_no_leakage():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    # Jockey A rides: R1 h1 (win), R2 h1 (3rd) + R2 h4 (2nd), R3 h1 (win).
    a_r1 = df[(df["race_id"] == "R1") & (df["jockey"] == "A")].iloc[0]
    a_r2 = df[(df["race_id"] == "R2") & (df["jockey"] == "A") & (df["horse_no"] == 1)].iloc[0]
    a_r3 = df[(df["race_id"] == "R3") & (df["jockey"] == "A")].iloc[0]

    # Before any race, jockey A has no history -> NaN (no prior rides).
    assert np.isnan(a_r1["jockey_win_rate"])

    # Before R2, jockey A's only prior ride was R1 win -> win_rate == 1.0.
    assert a_r2["jockey_win_rate"] == 1.0

    # Before R3, jockey A has 2 prior rides from R2 (both losses) plus the R1
    # win = 1 win / 3 rides = 0.333... Critically this must NOT reflect R3's
    # own outcome (which is also a win, which would make it 2/4 = 0.5 if
    # leakage occurred).
    assert abs(a_r3["jockey_win_rate"] - (1 / 3)) < 1e-9


def test_trainer_win_rate_excludes_future_races_no_leakage():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    # Trainer TA: R1 win (h1), R2 h1 loss + h4 loss, R3 h1 win.
    ta_r3 = df[(df["race_id"] == "R3") & (df["trainer"] == "TA")].iloc[0]
    # Before R3: TA had 3 prior runs (R1 h1 win, R2 h1 3rd, R2 h4 2nd) -> 1 win / 3 = 0.333...
    assert abs(ta_r3["trainer_win_rate"] - (1 / 3)) < 1e-9


def test_horse_prev_finish_and_runs_use_only_past_races():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    h1_r1 = df[(df["race_id"] == "R1") & (df["horse_id"] == "h1")].iloc[0]
    h1_r2 = df[(df["race_id"] == "R2") & (df["horse_id"] == "h1")].iloc[0]
    h1_r3 = df[(df["race_id"] == "R3") & (df["horse_id"] == "h1")].iloc[0]

    assert h1_r1["horse_runs"] == 0
    assert np.isnan(h1_r1["horse_prev_finish"])

    assert h1_r2["horse_runs"] == 1
    assert h1_r2["horse_prev_finish"] == 1  # h1 finished 1st in R1

    assert h1_r3["horse_runs"] == 2
    assert h1_r3["horse_prev_finish"] == 3  # h1 finished 3rd in R2 (most recent prior)


def test_field_size_matches_num_runners_and_sex_age_parsed():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    r1 = df[df["race_id"] == "R1"].set_index("horse_no")
    assert r1.loc[1, "field_size"] == 3
    assert r1.loc[1, "sex"] == "牡"
    assert r1.loc[1, "age"] == 3
    assert r1.loc[2, "sex"] == "牝"
    assert r1.loc[2, "age"] == 4
    assert r1.loc[3, "sex"] == "セ"
    assert r1.loc[3, "age"] == 5


def test_win_odds_present_but_not_named_as_a_feature_column():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)
    assert "win_odds" in df.columns
    assert "popularity" not in df.columns


def test_days_since_last_computed_from_prior_race_date():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)

    h1_r1 = df[(df["race_id"] == "R1") & (df["horse_id"] == "h1")].iloc[0]
    h1_r2 = df[(df["race_id"] == "R2") & (df["horse_id"] == "h1")].iloc[0]

    assert np.isnan(h1_r1["days_since_last"])
    assert h1_r2["days_since_last"] == 7  # 2024-01-08 - 2024-01-01


def test_output_row_count_matches_entries():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)
    total_entries = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert len(df) == total_entries


def test_required_columns_present():
    conn = build_basic_dataset()
    df = features.build_dataset(conn)
    expected = {
        "race_id", "date", "horse_id", "horse_no",
        "y_win", "y_top3", "win_odds",
        "distance", "surface", "going", "race_class", "field_size", "draw",
        "sex", "age", "weight_carried", "days_since_last",
        "horse_prev_finish", "horse_avg_finish3", "horse_avg_last3f",
        "jockey_win_rate", "trainer_win_rate", "horse_runs",
    }
    assert expected <= set(df.columns)
