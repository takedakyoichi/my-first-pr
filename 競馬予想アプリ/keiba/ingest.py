from keiba import db, discovery, fetcher, parser

RESULT_URL = "https://db.netkeiba.com/race/{race_id}/"


def ingest_race(conn, race_id, *, fetch=fetcher.fetch, parse=parser.parse_race_result) -> str:
    if race_id in db.processed_race_ids(conn):
        return "skip"
    html = fetch(RESULT_URL.format(race_id=race_id))
    parsed = parse(html, race_id)
    if not parsed["entries"] or not parsed["race"].get("date"):
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
