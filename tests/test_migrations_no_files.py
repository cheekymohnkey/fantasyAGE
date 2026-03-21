from backend.migrations import run_migrations


def test_run_migrations_with_no_sql_files(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    db_dir = tmp_path / "db"
    db_path = str(db_dir / "test.db")
    # Should not raise even when there are no .sql files
    run_migrations(db_path=db_path, migrations_dir=str(migrations_dir))
