import os
import sqlite3
import subprocess
import tempfile
import threading
import time
import requests


def _run_server(app_module, port=9000):
    # Run Flask app in a thread; disable reloader
    app_module.app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def test_e2e_i1_001_command_roundtrip():
    migrate_script = os.path.join(os.getcwd(), 'work-process', 'scripts', 'migrate.py')
    migrations_dir = os.path.join(os.getcwd(), 'work-process', 'db', 'migrations')

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, 'session.db')

        # Run migrations to temp DB
        r = subprocess.run([__import__('sys').executable, migrate_script, '--db', db_path, '--migrations', migrations_dir], capture_output=True, text=True)
        assert r.returncode == 0, f"Migrate failed: {r.stderr}"

        # set env so backend uses this DB
        os.environ['SESSION_DB'] = db_path

        # import backend app after env set and use Flask test client for HTTP-like roundtrip
        import importlib
        backend = importlib.import_module('backend.app')
        backend.app.config['TESTING'] = True
        # ensure backend module uses our temp DB path
        backend.DB_PATH = db_path

        payload = {'action_id': 'E2E_NOOP', 'idempotency_key': 'e2e-1-xyz'}
        with backend.app.test_client() as client:
            resp = client.post('/api/command', json=payload)
            assert resp.status_code == 200
            j = resp.get_json()
            assert j.get('status') == 'ok'

        # verify DB
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('SELECT action_id FROM command_receipts WHERE idempotency_key=?', ('e2e-1-xyz',))
        row = cur.fetchone()
        conn.close()
        assert row is not None and row[0] == 'E2E_NOOP'
