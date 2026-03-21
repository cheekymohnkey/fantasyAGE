import logging
import os

from .db import connect
from .timeutils import utc_now_z

logger = logging.getLogger("backend")


def _list_migration_files(migrations_dir: str) -> list[str]:
    try:
        files = [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
    except Exception:
        return []
    files.sort()
    return files


def _ensure_schema_migrations(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TEXT NOT NULL
    );"""
    )


def _applied_versions(conn) -> set[str]:
    cur = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def _apply_migration(conn, migrations_dir: str, filename: str) -> None:
    path = os.path.join(migrations_dir, filename)
    with open(path, encoding="utf-8") as fh:
        sql = fh.read()

    cur = conn.cursor()
    cur.executescript(sql)
    version = filename
    applied_at = utc_now_z()
    cur.execute(
        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, applied_at)
    )


def run_migrations(
    db_path: str, migrations_dir: str = os.path.join("work-process", "db", "migrations")
) -> None:
    if not os.path.isdir(migrations_dir):
        logger.info("Migrations directory not found: %s", migrations_dir)
        return

    files = _list_migration_files(migrations_dir)
    if not files:
        logger.info("No migration files found in %s", migrations_dir)
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = connect(db_path)
    try:
        _ensure_schema_migrations(conn)
        applied = _applied_versions(conn)

        for filename in files:
            if filename in applied:
                logger.info("Skipping already applied: %s", filename)
                continue
            logger.info("Applying migration: %s", filename)
            try:
                conn.execute("BEGIN")
                _apply_migration(conn, migrations_dir, filename)
                conn.commit()
                logger.info("Applied migration: %s", filename)
            except Exception:
                conn.rollback()
                logger.exception("Failed applying migration: %s", filename)
                raise
    finally:
        conn.close()
