import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import db_stats


def test_print_stats_on_fresh_empty_db_does_not_raise(tmp_path, capsys):
    db_path = tmp_path / "empty.db"
    # Create an empty sqlite file with no schema at all (fresh DB, collect.py never ran).
    conn = sqlite3.connect(db_path)
    conn.close()

    db_stats.print_stats(db_path)  # must not raise

    out = capsys.readouterr().out
    assert "no tables yet" in out.lower()
