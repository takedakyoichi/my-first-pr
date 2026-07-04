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
    horses = {}
    for e in parsed["entries"]:
        hid = e.get("horse_id")
        if hid:
            horses[hid] = {"horse_id": hid, "name": e.get("horse_name")}
    db.upsert_horses(conn, list(horses.values()))
    db.mark_progress(conn, race_id, "done")
    return "done"


def run(conn, date_start, date_end, *, fetch=fetcher.fetch,
        parse=parser.parse_race_result, limit=None, logger=None) -> dict:
    summary = {"done": 0, "empty": 0, "skip": 0, "error": 0}
    attempted = 0
    for d in discovery.jra_race_dates(date_start, date_end):
        date_tally = {"done": 0, "empty": 0, "skip": 0, "error": 0}
        for race_id in discovery.race_ids_for_date(d, fetch=fetch):
            if limit is not None and attempted >= limit:
                break
            try:
                status = ingest_race(conn, race_id, fetch=fetch, parse=parse)
            except Exception:
                db.mark_progress(conn, race_id, "error")
                status = "error"
            summary[status] = summary.get(status, 0) + 1
            date_tally[status] = date_tally.get(status, 0) + 1
            if status != "skip":
                attempted += 1
        if logger is not None:
            cum_done = summary["done"]
            logger(
                f"{d} done={date_tally['done']} empty={date_tally['empty']} "
                f"error={date_tally['error']} skip={date_tally['skip']} "
                f"(cum done={cum_done})"
            )
        if limit is not None and attempted >= limit:
            break
    return summary
