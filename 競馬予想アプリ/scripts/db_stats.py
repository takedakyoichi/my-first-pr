"""race.db の内容を集計して表示する簡易統計スクリプト。"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from keiba import config


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def print_stats(db_path) -> None:
    if not Path(db_path).exists():
        print(f"DB not found: {db_path}")
        print("先に scripts/collect.py を実行してください。")
        return

    conn = sqlite3.connect(db_path)
    try:
        if not _table_exists(conn, "races"):
            print(f"DB path: {db_path}")
            print("DB has no tables yet -- run collect.py first.")
            return

        def count(table):
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        n_races = count("races")
        n_entries = count("entries")
        n_payouts = count("payouts")

        date_range = conn.execute(
            "SELECT MIN(date), MAX(date) FROM races WHERE date IS NOT NULL"
        ).fetchone()

        progress = dict(conn.execute(
            "SELECT status, COUNT(*) FROM ingest_progress GROUP BY status"
        ).fetchall())

        print(f"DB path: {db_path}")
        print(f"races:   {n_races}")
        print(f"entries: {n_entries}")
        print(f"payouts: {n_payouts}")
        print(f"date range: {date_range[0]} .. {date_range[1]}")
        print(f"ingest_progress: {progress}")
    finally:
        conn.close()


def main():
    print_stats(config.DB_PATH)


if __name__ == "__main__":
    main()
