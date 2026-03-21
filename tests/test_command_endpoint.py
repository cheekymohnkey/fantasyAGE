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
    ret = subprocess.run(
        [sys.executable, migrate_script, "--db", db_path, "--migrations", migrations_dir],
        capture_output=True,
        text=True,
    )
    assert ret.returncode == 0, f"Migrations failed: {ret.stderr}"
    return db_path


def _build_client(db_path):
    backend_app.runtime = backend_app.load_runtime_config(default_login_id="default")
    backend_app.runtime = backend_app.runtime.__class__(
        db_path=db_path,
        default_login_id=backend_app.runtime.default_login_id,
        default_campaign_id=backend_app.runtime.default_campaign_id,
        default_session_id=backend_app.runtime.default_session_id,
        implicit_session_create=True,
    )
    return backend_app.app.test_client()


def test_command_endpoint_records_receipt(tmp_path):
    db_path = _setup_temp_db(tmp_path)

    client = _build_client(db_path)

    payload = {
        "action_id": "NO_OP_TEST",
        "idempotency_key": "test-key-123",
        "metadata": {"login_id": "default", "campaign_id": "camp-1", "session_id": "sess-1"},
    }
    resp = client.post("/api/command", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert data.get("context", {}).get("campaign_id") == "camp-1"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT action_id, idempotency_key FROM command_receipts WHERE idempotency_key=?",
        ("test-key-123",),
    )
    row = cur.fetchone()
    conn.close()

    assert row is not None and row[0] == "NO_OP_TEST"


def test_command_endpoint_idempotent_replay(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    payload = {
        "action_id": "NO_OP_TEST",
        "idempotency_key": "same-key-1",
        "metadata": {"login_id": "default", "campaign_id": "camp-1", "session_id": "sess-1"},
    }
    first = client.post("/api/command", json=payload)
    second = client.post("/api/command", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json() == second.get_json()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM command_receipts WHERE idempotency_key=?", ("same-key-1",))
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1


def test_owner_scope_mismatch_returns_403(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    payload = {
        "action_id": "NO_OP_TEST",
        "idempotency_key": "owner-key-1",
        "metadata": {"login_id": "alice", "campaign_id": "camp-1", "session_id": "sess-1"},
    }
    resp = client.post("/api/command", json=payload, headers={"X-Login-Id": "bob"})
    assert resp.status_code == 403
    data = resp.get_json()
    assert data.get("reason_code") == "precondition.owner_scope_mismatch"


def test_invalid_payload_returns_reason_code(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    payload = {"action_id": "", "idempotency_key": "k"}
    resp = client.post("/api/command", json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("reason_code") == "validation.invalid_payload"


def test_legacy_empty_receipt_is_upgraded_on_replay(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    created_at = "2026-03-21T00:00:00Z"
    cur.execute(
        (
            "INSERT OR IGNORE INTO campaigns (login_id, campaign_id, name, status, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
        ),
        ("default", "default", "Default Campaign", "active", created_at, created_at),
    )
    cur.execute(
        (
            "INSERT OR IGNORE INTO sessions (login_id, campaign_id, session_id, "
            "state_version, scene_mode, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ),
        ("default", "default", "default", 0, "default", "{}", created_at),
    )
    cur.execute(
        (
            "INSERT INTO command_receipts (login_id, campaign_id, session_id, "
            "idempotency_key, action_id, action_result_json, correlation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        ("default", "default", "default", "test-noop-1", "NO_OP", "{}", "", created_at),
    )
    conn.commit()
    conn.close()

    payload = {
        "action_id": "NO_OP",
        "idempotency_key": "test-noop-1",
        "payload": {"noop": True, "player_name": "Snuggz"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    resp = client.post("/api/command", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("status") == "ok"
    assert body.get("action_id") == "NO_OP"
    assert body.get("idempotency_key") == "test-noop-1"
