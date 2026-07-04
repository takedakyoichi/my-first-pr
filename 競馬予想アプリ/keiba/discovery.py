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
