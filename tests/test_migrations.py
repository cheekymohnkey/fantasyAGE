import os
import sqlite3
import subprocess
import sys
import tempfile


def test_migrations_apply_and_seed():
    script = os.path.join(os.getcwd(), "work-process", "scripts", "migrate.py")
    migrations_dir = os.path.join(os.getcwd(), "work-process", "db", "migrations")

    assert os.path.isfile(script), f"Migration script not found at {script}"
    assert os.path.isdir(migrations_dir), f"Migrations dir not found at {migrations_dir}"

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "session.db")

        completed = subprocess.run(
            [sys.executable, script, "--db", db_path, "--migrations", migrations_dir],
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, (
            f"Migration runner failed:\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Expected tables
        expected_tables = (
            "campaigns",
            "sessions",
            "runtime_config",
            "schema_migrations",
            "command_receipts",
        )
        for tbl in expected_tables:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,))
            assert cur.fetchone() is not None, f"Expected table {tbl} missing"

        # runtime_config seed
        cur.execute("SELECT config_value FROM runtime_config WHERE config_key='default_login_id'")
        row = cur.fetchone()
        assert row is not None and row[0] == "default", 'default_login_id not seeded as "default"'

        # migrations recorded
        cur.execute("SELECT version FROM schema_migrations")
        versions = {r[0] for r in cur.fetchall()}
        assert any(v.startswith("0001") for v in versions), (
            "0001 migration not recorded in schema_migrations"
        )
        assert any(v.startswith("0002") for v in versions), (
            "0002 migration not recorded in schema_migrations"
        )

        conn.close()
