from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sqlite3
import os
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
DB_PATH = os.environ.get('SESSION_DB', os.path.join('work-process', 'runtime', 'session.db'))
DEFAULT_LOGIN_ID = 'default'

# Logging setup
LOG_DIR = os.path.join(os.getcwd(), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'backend_requests.log')
logger = logging.getLogger('backend')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        logger.exception('Failed to create file handler for logging')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def _list_migration_files(migrations_dir):
    try:
        files = [f for f in os.listdir(migrations_dir) if f.endswith('.sql')]
    except Exception:
        return []
    files.sort()
    return files


def _ensure_schema_migrations(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TEXT NOT NULL
    );""")


def _applied_versions(conn):
    cur = conn.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def _apply_migration(conn, migrations_dir, filename):
    path = os.path.join(migrations_dir, filename)
    with open(path, 'r', encoding='utf-8') as fh:
        sql = fh.read()

    cur = conn.cursor()
    cur.executescript(sql)
    version = filename
    applied_at = datetime.utcnow().isoformat() + 'Z'
    cur.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, applied_at))


def run_migrations(db_path=DB_PATH, migrations_dir=os.path.join('work-process', 'db', 'migrations')):
    if not os.path.isdir(migrations_dir):
        logger.info('Migrations directory not found: %s', migrations_dir)
        return

    files = _list_migration_files(migrations_dir)
    if not files:
        logger.info('No migration files found in %s', migrations_dir)
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON;')
    try:
        _ensure_schema_migrations(conn)
        applied = _applied_versions(conn)

        for f in files:
            if f in applied:
                logger.info('Skipping already applied: %s', f)
                continue

            logger.info('Applying migration: %s', f)
            try:
                conn.execute('BEGIN')
                _apply_migration(conn, migrations_dir, f)
                conn.commit()
                logger.info('Applied migration: %s', f)
            except Exception:
                conn.rollback()
                logger.exception('Failed applying migration: %s', f)
                raise

    finally:
        conn.close()


# Ensure migrations are applied on backend startup so DB is ready for requests
try:
    run_migrations()
except Exception:
    logger.exception('Migration runner failed during startup')


# Load runtime config values (like default_login_id) after migrations
try:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT config_value FROM runtime_config WHERE config_key='default_login_id'")
        row = cur.fetchone()
        if row and row[0]:
            DEFAULT_LOGIN_ID = row[0]
            logger.info('Loaded default_login_id=%s from runtime_config', DEFAULT_LOGIN_ID)
        else:
            logger.info('Using fallback default_login_id=%s', DEFAULT_LOGIN_ID)
    except Exception:
        logger.exception('Failed to load runtime_config; using defaults')
    finally:
        conn.close()
except Exception:
    logger.exception('Unable to open DB to read runtime_config')


@app.post('/api/command')
def command():
    try:
        data = request.get_json()
    except Exception as e:
        logger.exception('Invalid JSON received')
        return jsonify({'error': 'invalid json'}), 400

    if not data:
        logger.warning('Empty JSON payload received from %s', request.remote_addr)
        return jsonify({'error': 'invalid json'}), 400

    # Minimal idempotent no-op handler: record a command_receipt and return success
    idempotency_key = data.get('idempotency_key') or str(uuid.uuid4())
    action_id = data.get('action_id', 'NO_OP')
    login_id = 'default'
    campaign_id = 'default'
    session_id = 'default'
    created_at = datetime.utcnow().isoformat() + 'Z'

    logger.info('Incoming command from %s: idempotency_key=%s action_id=%s', request.remote_addr, idempotency_key, action_id)

    conn = get_conn()
    try:
        cur = conn.cursor()
        # ensure owning campaign and session exist to satisfy FK constraints
        try:
            cur.execute('INSERT OR IGNORE INTO campaigns (login_id, campaign_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (login_id, campaign_id, 'Default Campaign', 'active', created_at, created_at))
            conn.commit()
            cur.execute('INSERT OR IGNORE INTO sessions (login_id, campaign_id, session_id, state_version, scene_mode, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (login_id, campaign_id, session_id, 0, 'default', '{}', created_at))
            conn.commit()
        except Exception:
            logger.exception('Failed to ensure campaign/session for FK constraints')
            # continue and let the main insert surface an error if necessary
        # store a simple receipt
        cur.execute('''INSERT OR REPLACE INTO command_receipts
            (login_id, campaign_id, session_id, idempotency_key, action_id, action_result_json, correlation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (login_id, campaign_id, session_id, idempotency_key, action_id, '{}', data.get('correlation_id',''), created_at))
        conn.commit()
        logger.info('Recorded command_receipt idempotency_key=%s', idempotency_key)
    except Exception:
        logger.exception('Failed to record command_receipt for idempotency_key=%s', idempotency_key)
        return jsonify({'error': 'internal_error'}), 500
    finally:
        conn.close()

    # Return canonical command/result contract fields for frontend normalization:
    response = {
        'status': 'ok',
        'action_id': action_id,
        'action': action_id,
        'idempotency_key': idempotency_key,
        'idempotency': idempotency_key,
        'action_result': {},
        'action_result_json': '{}',
        'event': None,
    }
    return jsonify(response)


if __name__ == '__main__':
    # Log startup
    logger.info('Starting backend on 0.0.0.0:8000, DB=%s', DB_PATH)
    app.run(host='0.0.0.0', port=8000)
