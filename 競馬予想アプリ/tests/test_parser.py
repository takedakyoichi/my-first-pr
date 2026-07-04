import pathlib
import pytest

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
pytestmark = pytest.mark.skipif(
    not (FIX / "race_result_sample.html").exists(),
    reason="run scripts/save_fixture.py locally to fetch real netkeiba HTML, then these validate the parser")

from keiba import parser


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
