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
             "time_sec": 95.0, "last_3f": 33.5, "margin": "",
             "horse_name": "ホースA"},
            {"horse_id": "h2", "horse_no": 2, "draw": 2, "jockey": "B",
             "trainer": "T2", "sex_age": "牝4", "weight_carried": 55.0,
             "win_odds": 5.0, "popularity": 2, "finish_pos": 2,
             "time_sec": 95.2, "last_3f": 33.9, "margin": "1",
             "horse_name": "ホースB"},
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
    rows = conn.execute(
        "SELECT horse_id, name FROM horses ORDER BY horse_id"
    ).fetchall()
    assert rows == [("h1", "ホースA"), ("h2", "ホースB")]


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


def test_ingest_race_missing_date_is_empty():
    conn = make_conn()

    def fake_parse_missing_date(html, race_id):
        return {
            "race": {"race_id": race_id, "date": None, "course": None,
                     "distance": 1600, "surface": "芝", "going": "良",
                     "race_class": "G1", "num_runners": 2, "weather": "晴"},
            "entries": [
                {"horse_id": "h1", "horse_no": 1, "draw": 1, "jockey": "A",
                 "trainer": "T", "sex_age": "牡3", "weight_carried": 55.0,
                 "win_odds": 2.1, "popularity": 1, "finish_pos": 1,
                 "time_sec": 95.0, "last_3f": 33.5, "margin": ""},
            ],
            "payouts": [{"bet_type": "win", "combination": "1", "payout": 210,
                         "popularity": 1}],
        }

    status = ingest.ingest_race(conn, "202112260111",
                                fetch=lambda url, **k: "<html>", parse=fake_parse_missing_date)
    assert status == "empty"
    n = conn.execute("SELECT COUNT(*) FROM races").fetchone()[0]
    assert n == 0


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


def test_run_isolates_errors(monkeypatch):
    conn = make_conn()
    monkeypatch.setattr(ingest.discovery, "jra_race_dates", lambda s, e: ["20211226"])
    monkeypatch.setattr(
        ingest.discovery, "race_ids_for_date",
        lambda d, fetch=None: ["202112260111", "BADRACEID0001"],
    )

    def route_parse(html, race_id):
        if race_id == "BADRACEID0001":
            raise IndexError("odd page layout, missing column")
        return fake_parse_full(html, race_id)

    # This must NOT raise -- a single bad race must not abort the whole run.
    summary = ingest.run(conn, "2021-12-26", "2021-12-26",
                         fetch=lambda url, **k: "<html>", parse=route_parse)

    assert summary["done"] == 1
    assert summary["error"] == 1

    status = conn.execute(
        "SELECT status FROM ingest_progress WHERE race_id=?",
        ("BADRACEID0001",),
    ).fetchone()[0]
    assert status == "error"

    # errored races are NOT in processed_race_ids, so they will be retried
    assert "BADRACEID0001" not in db.processed_race_ids(conn)


def test_run_limit_stops_after_n_attempted_races(monkeypatch):
    conn = make_conn()
    monkeypatch.setattr(ingest.discovery, "jra_race_dates", lambda s, e: ["20211226"])
    monkeypatch.setattr(
        ingest.discovery, "race_ids_for_date",
        lambda d, fetch=None: ["202112260111", "202112260222", "202112260333", "202112260444"],
    )

    summary = ingest.run(conn, "2021-12-26", "2021-12-26",
                         fetch=lambda url, **k: "<html>", parse=fake_parse_full,
                         limit=2)

    attempted = summary["done"] + summary["empty"] + summary["error"]
    assert attempted == 2
    # Not all 4 available races were processed -- the limit stopped iteration early.
    assert len(db.processed_race_ids(conn)) == 2


def test_run_limit_does_not_count_already_skipped_races(monkeypatch):
    conn = make_conn()
    monkeypatch.setattr(ingest.discovery, "jra_race_dates", lambda s, e: ["20211226"])
    monkeypatch.setattr(
        ingest.discovery, "race_ids_for_date",
        lambda d, fetch=None: ["202112260111", "202112260222", "202112260333"],
    )

    # Pre-process the first race so it will be skipped on the next run.
    ingest.ingest_race(conn, "202112260111", fetch=lambda url, **k: "<html>", parse=fake_parse_full)

    summary = ingest.run(conn, "2021-12-26", "2021-12-26",
                         fetch=lambda url, **k: "<html>", parse=fake_parse_full,
                         limit=2)

    # The pre-processed race is skipped (doesn't consume budget), so the
    # limit still allows 2 NEW races to be attempted.
    assert summary["skip"] == 1
    attempted = summary["done"] + summary["empty"] + summary["error"]
    assert attempted == 2


def test_run_logger_receives_one_message_per_date(monkeypatch):
    conn = make_conn()
    monkeypatch.setattr(ingest.discovery, "jra_race_dates", lambda s, e: ["20211226", "20211227"])

    def fake_race_ids(d, fetch=None):
        return ["202112260111"] if d == "20211226" else ["202112270111"]

    monkeypatch.setattr(ingest.discovery, "race_ids_for_date", fake_race_ids)

    captured = []
    ingest.run(conn, "2021-12-26", "2021-12-27",
              fetch=lambda url, **k: "<html>", parse=fake_parse_full,
              logger=lambda m: captured.append(m))

    assert len(captured) == 2
    assert "20211226" in captured[0]
    assert "done=1" in captured[0]
    assert "20211227" in captured[1]
    # running cumulative tally across dates
    assert "cum done=2" in captured[1]


def test_run_default_logger_produces_no_output(monkeypatch, capsys):
    conn = make_conn()
    monkeypatch.setattr(ingest.discovery, "jra_race_dates", lambda s, e: ["20211226"])
    monkeypatch.setattr(ingest.discovery, "race_ids_for_date",
                        lambda d, fetch=None: ["202112260111"])

    ingest.run(conn, "2021-12-26", "2021-12-26",
              fetch=lambda url, **k: "<html>", parse=fake_parse_full)

    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""


def test_ingest_race_marks_error_then_retries():
    conn = make_conn()
    calls = {"n": 0}

    def flaky_parse(html, race_id):
        calls["n"] += 1
        raise RuntimeError("boom")

    try:
        ingest.ingest_race(conn, "202112260111",
                           fetch=lambda url, **k: "<html>", parse=flaky_parse)
        raised = False
    except RuntimeError:
        raised = True

    # ingest_race itself does not swallow the exception -- that's run()'s job.
    assert raised is True
    assert calls["n"] == 1
    assert "202112260111" not in db.processed_race_ids(conn)
