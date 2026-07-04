"""フィクスチャ取得スクリプト（ローカル実行専用）。

実際のnetkeibaページを1回だけ取得し、tests/fixtures/ 配下にHTMLとして保存する。
保存後、tests/test_parser.py と tests/test_discovery.py の @skipif ガードが
外れ、実HTMLに対してパーサ/発見ロジックを検証できるようになる。

使い方:
  1. 下記の RACE_URL / LIST_URL を、実在する直近のJRAレース結果ページ・
     開催日一覧ページのURLに書き換える。
     - RACE_URL: https://db.netkeiba.com/race/<race_id>/ 形式
     - LIST_URL: https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=<YYYYMMDD> 形式
  2. `python3 scripts/save_fixture.py` を実行する（keiba.fetcher 経由なので
     礼儀正しいスリープ・キャッシュが効く）。
  3. tests/fixtures/race_result_sample.html と race_list_sample.html が
     生成されたことを確認する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from keiba import fetcher

# --- ここを実在するURLに書き換えてから実行する ---
RACE_URL = "https://db.netkeiba.com/race/202105021211/"
LIST_URL = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=20211226"

FIX_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def save(url: str, out_name: str) -> None:
    html = fetcher.fetch(url, encoding="euc-jp")
    FIX_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIX_DIR / out_name
    out_path.write_text(html, encoding="utf-8")
    print(f"saved {url} -> {out_path}")


def main():
    save(RACE_URL, "race_result_sample.html")
    save(LIST_URL, "race_list_sample.html")


if __name__ == "__main__":
    main()
