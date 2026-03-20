from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sqlite3
import os
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
DB_PATH = os.path.join('work-process', 'runtime', 'session.db')

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

    return jsonify({'status': 'ok', 'action_id': action_id, 'idempotency_key': idempotency_key})


if __name__ == '__main__':
    # Log startup
    logger.info('Starting backend on 0.0.0.0:8000, DB=%s', DB_PATH)
    app.run(host='0.0.0.0', port=8000)
