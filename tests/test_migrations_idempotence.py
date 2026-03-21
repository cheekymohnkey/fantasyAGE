import os
import subprocess
import sys
import tempfile


def test_migrations_idempotence_runs_twice():
    script = os.path.join(os.getcwd(), "work-process", "scripts", "migrate.py")
    migrations_dir = os.path.join(os.getcwd(), "work-process", "db", "migrations")

    assert os.path.isfile(script), f"Migration script not found at {script}"
    assert os.path.isdir(migrations_dir), f"Migrations dir not found at {migrations_dir}"

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "session.db")

        # First run
        first = subprocess.run(
            [sys.executable, script, "--db", db_path, "--migrations", migrations_dir],
            capture_output=True,
            text=True,
        )
        assert first.returncode == 0, f"First migration run failed:\nSTDOUT:\n{first.stdout}\nSTDERR:\n{first.stderr}"

        # Second run should be a no-op and still succeed
        second = subprocess.run(
            [sys.executable, script, "--db", db_path, "--migrations", migrations_dir],
            capture_output=True,
            text=True,
        )
        assert second.returncode == 0, f"Second migration run failed:\nSTDOUT:\n{second.stdout}\nSTDERR:\n{second.stderr}"
        assert "Skipping already applied" in second.stdout or "No migration files found." in second.stdout
