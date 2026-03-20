import os
import tempfile
import sqlite3

from backend import app as backend_app


def test_command_endpoint_records_receipt(tmp_path):
    # use a temporary DB for isolation
    db_dir = tmp_path / 'runtime'
    db_dir.mkdir()
    db_path = str(db_dir / 'session.db')

    # ensure migrations apply to this temp DB
    migrate_script = os.path.join(os.getcwd(), 'work-process', 'scripts', 'migrate.py')
    migrations_dir = os.path.join(os.getcwd(), 'work-process', 'db', 'migrations')
    ret = __import__('subprocess').run([__import__('sys').executable, migrate_script, '--db', db_path, '--migrations', migrations_dir], capture_output=True, text=True)
    assert ret.returncode == 0, f"Migrations failed: {ret.stderr}"

    # patch app DB path to temp DB for this test
    backend_app.DB_PATH = db_path
    client = backend_app.app.test_client()

    payload = {'action_id': 'NO_OP_TEST', 'idempotency_key': 'test-key-123'}
    resp = client.post('/api/command', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('status') == 'ok'

    # verify DB contains the receipt
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT action_id, idempotency_key FROM command_receipts WHERE idempotency_key=?", ('test-key-123',))
    row = cur.fetchone()
    conn.close()

    assert row is not None and row[0] == 'NO_OP_TEST'
