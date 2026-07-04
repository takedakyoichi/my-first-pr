"""収集CLI: 期間を指定して race.db に収集する。中断しても再実行で続きから。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from keiba import config, db, ingest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=config.DATE_START)
    ap.add_argument("--end", default=config.DATE_END)
    args = ap.parse_args()

    conn = db.connect(config.DB_PATH)
    db.init_schema(conn)
    print(f"collecting {args.start} .. {args.end} -> {config.DB_PATH}")
    summary = ingest.run(conn, args.start, args.end)
    print("summary:", summary)


if __name__ == "__main__":
    main()
