import os
import sqlite3

from backend import migrations as migrations_mod


def test_migration_applied_at_is_utc_z(tmp_path):
    db_path = str(tmp_path / "session.db")
    migrations_dir = str(tmp_path / "migrations_ts")
    os.makedirs(migrations_dir, exist_ok=True)
    fname = "0007_ts_test.sql"
    path = os.path.join(migrations_dir, fname)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("CREATE TABLE ts_test (id INTEGER PRIMARY KEY);\n")

    migrations_mod.run_migrations(db_path, migrations_dir=migrations_dir)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT applied_at FROM schema_migrations WHERE version=?", (fname,))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    applied_at = row[0]
    # Expect ISO8601 ending with Z (UTC)
    assert applied_at.endswith("Z")
    # should not contain a timezone offset like +00:00
    assert "+00:" not in applied_at
