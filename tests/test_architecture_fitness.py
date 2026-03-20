import os
import sqlite3
import subprocess
import sys

from backend import app as backend_app


def _setup_temp_db(tmp_path):
    db_dir = tmp_path / "runtime"
    db_dir.mkdir()
    db_path = str(db_dir / "session.db")
    migrate_script = os.path.join(os.getcwd(), "work-process", "scripts", "migrate.py")
    migrations_dir = os.path.join(os.getcwd(), "work-process", "db", "migrations")
    completed = subprocess.run(
        [sys.executable, migrate_script, "--db", db_path, "--migrations", migrations_dir],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return db_path


def _client_for_db(db_path):
    backend_app.runtime = backend_app.load_runtime_config(default_login_id="default")
    backend_app.runtime = backend_app.runtime.__class__(
        db_path=db_path,
        default_login_id="default",
        default_campaign_id="default",
        default_session_id="default",
    )
    return backend_app.app.test_client()


def test_atomicity_no_receipt_written_on_owner_scope_error(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _client_for_db(db_path)

    payload = {
        "action_id": "NO_OP",
        "idempotency_key": "atomic-owner-fail",
        "metadata": {"login_id": "alice", "campaign_id": "camp-1", "session_id": "sess-1"},
    }

    response = client.post("/api/command", json=payload, headers={"X-Login-Id": "bob"})
    assert response.status_code == 403

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM command_receipts WHERE idempotency_key='atomic-owner-fail'")
    assert cur.fetchone()[0] == 0
    conn.close()


def test_default_scope_applied_when_metadata_missing(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _client_for_db(db_path)

    payload = {
        "action_id": "NO_OP",
        "idempotency_key": "default-scope-1",
    }
    response = client.post("/api/command", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["context"]["login_id"] == "default"
    assert body["context"]["campaign_id"] == "default"
    assert body["context"]["session_id"] == "default"
