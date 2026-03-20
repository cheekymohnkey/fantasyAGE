#!/usr/bin/env python3
"""Simple SQLite migration runner.

Usage: python work-process/scripts/migrate.py [--db path/to/session.db] [--migrations path/to/migrations]

This runner applies forward-only SQL files from the migrations directory in lexical order.
Each migration filename should start with a numeric/semantic prefix, e.g. `0001_initial.sql`.
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime


def list_migration_files(migrations_dir):
    files = [f for f in os.listdir(migrations_dir) if f.endswith('.sql')]
    files.sort()
    return files


def ensure_schema_migrations(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TEXT NOT NULL
    );""")


def applied_versions(conn):
    cur = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def apply_migration(conn, migrations_dir, filename):
    path = os.path.join(migrations_dir, filename)
    with open(path, 'r', encoding='utf-8') as fh:
        sql = fh.read()

    cur = conn.cursor()
    try:
        cur.executescript(sql)
        version = filename
        applied_at = datetime.utcnow().isoformat() + 'Z'
        cur.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, applied_at))
    except Exception:
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=os.path.join('work-process', 'runtime', 'session.db'))
    parser.add_argument('--migrations', default=os.path.join('work-process', 'db', 'migrations'))
    args = parser.parse_args()

    migrations_dir = args.migrations
    if not os.path.isdir(migrations_dir):
        print(f"Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    files = list_migration_files(migrations_dir)
    if not files:
        print("No migration files found.")
        sys.exit(0)

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.execute('PRAGMA foreign_keys = ON;')

    try:
        ensure_schema_migrations(conn)
        applied = applied_versions(conn)

        for f in files:
            if f in applied:
                print(f"Skipping already applied: {f}")
                continue

            print(f"Applying migration: {f}")
            try:
                conn.execute('BEGIN')
                apply_migration(conn, migrations_dir, f)
                conn.commit()
                print(f"Applied {f}")
            except Exception as e:
                conn.rollback()
                print(f"Failed applying {f}: {e}")
                sys.exit(2)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
