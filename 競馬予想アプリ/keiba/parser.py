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
    intro = soup.select_one(".diary_snap_cut, .data_intro, .racedata")
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
