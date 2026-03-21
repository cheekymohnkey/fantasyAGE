import sqlite3
import pytest

from backend.migrations import run_migrations


def test_failing_migration_rolls_back_and_records_previous(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # good migration that should apply
    good = migrations_dir / "001_create.sql"
    good.write_text("CREATE TABLE foo (id INTEGER PRIMARY KEY);")

    # bad migration that will raise sqlite error
    bad = migrations_dir / "002_bad.sql"
    bad.write_text("CREAT TABLE broken;")

    db_path = tmp_path / "db" / "test.sqlite"

    with pytest.raises(sqlite3.Error):
        run_migrations(str(db_path), str(migrations_dir))

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_migrations ORDER BY version")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()

    assert "001_create.sql" in rows
    assert "002_bad.sql" not in rows
