import pathlib
import pytest

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
pytestmark = pytest.mark.skipif(
    not (FIX / "race_list_sample.html").exists(),
    reason="run scripts/save_fixture.py locally to fetch real netkeiba HTML, then these validate discovery")

from keiba import discovery


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
