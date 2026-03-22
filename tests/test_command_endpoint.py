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


def _build_client(db_path, implicit_session_create=True):
    backend_app.runtime = backend_app.load_runtime_config(default_login_id="default")
    backend_app.runtime = backend_app.runtime.__class__(
        db_path=db_path,
        default_login_id=backend_app.runtime.default_login_id,
        default_campaign_id=backend_app.runtime.default_campaign_id,
        default_session_id=backend_app.runtime.default_session_id,
        implicit_session_create=implicit_session_create,
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


def test_campaign_commands_create_list_open_archive(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    create_payload = {
        "action_id": "campaign.create",
        "idempotency_key": "camp-create-1",
        "payload": {"campaign_id": "camp-x", "name": "Adventure X"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    resp = client.post("/api/command", json=create_payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body.get("status") == "ok"
    assert body.get("action_result", {}).get("campaign_id") == "camp-x"
    assert body.get("action_result", {}).get("status") == "active"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT campaign_id, name, status FROM campaigns WHERE campaign_id=?", ("camp-x",))
    row = cur.fetchone()
    conn.close()
    assert row == ("camp-x", "Adventure X", "active")

    # list campaigns for current login
    list_payload = {
        "action_id": "campaign.list",
        "idempotency_key": "camp-list-1",
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    list_resp = client.post("/api/command", json=list_payload)
    assert list_resp.status_code == 200
    campaigns = list_resp.get_json().get("action_result", {}).get("campaigns", [])
    assert any(c.get("campaign_id") == "camp-x" for c in campaigns)

    # open campaign
    open_payload = {
        "action_id": "campaign.open",
        "idempotency_key": "camp-open-1",
        "payload": {"campaign_id": "camp-x"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    open_resp = client.post("/api/command", json=open_payload)
    assert open_resp.status_code == 200
    assert open_resp.get_json().get("action_result", {}).get("campaign_id") == "camp-x"

    # archive campaign
    archive_payload = {
        "action_id": "campaign.archive",
        "idempotency_key": "camp-archive-1",
        "payload": {"campaign_id": "camp-x"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    archive_resp = client.post("/api/command", json=archive_payload)
    assert archive_resp.status_code == 200
    assert archive_resp.get_json().get("action_result", {}).get("status") == "archived"

    # open archived campaign should fail
    open_archived_payload = {
        **open_payload,
        "idempotency_key": "camp-open-2",
    }
    open_archived = client.post("/api/command", json=open_archived_payload)
    assert open_archived.status_code == 412


def test_session_commands_create_list_open(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    # Create campaign context
    create_campaign_payload = {
        "action_id": "campaign.create",
        "idempotency_key": "camp-create-for-session",
        "payload": {"campaign_id": "camp-x", "name": "Adventure X"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    create_campaign_resp = client.post("/api/command", json=create_campaign_payload)
    assert create_campaign_resp.status_code == 200

    # Create a session under the new campaign
    create_session_payload = {
        "action_id": "session.create",
        "idempotency_key": "sess-create-1",
        "payload": {"campaign_id": "camp-x", "session_id": "sess-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    create_session_resp = client.post("/api/command", json=create_session_payload)
    assert create_session_resp.status_code == 200
    assert create_session_resp.get_json().get("action_result", {}).get("session_id") == "sess-1"

    # List sessions in campaign
    list_session_payload = {
        "action_id": "session.list",
        "idempotency_key": "sess-list-1",
        "payload": {"campaign_id": "camp-x"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    list_session_resp = client.post("/api/command", json=list_session_payload)
    assert list_session_resp.status_code == 200
    sessions = list_session_resp.get_json().get("action_result", {}).get("sessions", [])
    assert any(s.get("session_id") == "sess-1" for s in sessions)

    # Open session
    open_session_payload = {
        "action_id": "session.open",
        "idempotency_key": "sess-open-1",
        "payload": {"campaign_id": "camp-x", "session_id": "sess-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    open_session_resp = client.post("/api/command", json=open_session_payload)
    assert open_session_resp.status_code == 200
    assert open_session_resp.get_json().get("action_result", {}).get("session_id") == "sess-1"

    # Open nonexistent session should fail
    open_session_missing_payload = {
        **open_session_payload,
        "idempotency_key": "sess-open-2",
        "payload": {"campaign_id": "camp-x", "session_id": "sess-missing"},
    }
    open_missing_resp = client.post("/api/command", json=open_session_missing_payload)
    assert open_missing_resp.status_code == 412


def test_entity_crud_lifecycle(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    # ensure session exists
    session_payload = {
        "action_id": "session.create",
        "idempotency_key": "sess-create-entity",
        "payload": {"campaign_id": "default", "session_id": "session-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    resp = client.post("/api/command", json=session_payload)
    assert resp.status_code == 200

    # create entity
    create_entity = {
        "action_id": "entity.create",
        "idempotency_key": "entity-create-1",
        "payload": {"entity_type": "character", "entity_id": "char-1", "payload": {"name": "Gus"}},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-1"},
    }
    create_resp = client.post("/api/command", json=create_entity)
    assert create_resp.status_code == 200
    assert create_resp.get_json().get("action_result", {}).get("entity_id") == "char-1"

    # read entity
    read_entity = {
        "action_id": "entity.read",
        "idempotency_key": "entity-read-1",
        "payload": {"entity_type": "character", "entity_id": "char-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-1"},
    }
    read_resp = client.post("/api/command", json=read_entity)
    assert read_resp.status_code == 200
    assert read_resp.get_json().get("action_result", {}).get("payload", {}).get("name") == "Gus"

    # update entity
    update_entity = {
        "action_id": "entity.update",
        "idempotency_key": "entity-update-1",
        "payload": {"entity_type": "character", "entity_id": "char-1", "payload": {"name": "Gus Updated"}},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-1"},
    }
    update_resp = client.post("/api/command", json=update_entity)
    assert update_resp.status_code == 200
    assert update_resp.get_json().get("action_result", {}).get("payload", {}).get("name") == "Gus Updated"

    # list entities
    list_entity = {
        "action_id": "entity.list",
        "idempotency_key": "entity-list-1",
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-1"},
    }
    list_resp = client.post("/api/command", json=list_entity)
    assert list_resp.status_code == 200
    entities = list_resp.get_json().get("action_result", {}).get("entities", [])
    assert any(e.get("entity_id") == "char-1" for e in entities)

    # delete entity
    delete_entity = {
        "action_id": "entity.delete",
        "idempotency_key": "entity-delete-1",
        "payload": {"entity_type": "character", "entity_id": "char-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-1"},
    }
    delete_resp = client.post("/api/command", json=delete_entity)
    assert delete_resp.status_code == 200
    assert delete_resp.get_json().get("action_result", {}).get("status") == "deleted"

    # read deleted should fail 412
    read_deleted = client.post("/api/command", json={
        "action_id": "entity.read",
        "idempotency_key": "entity-read-2",
        "payload": {"entity_type": "character", "entity_id": "char-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-1"},
    })
    assert read_deleted.status_code == 412


def test_entity_canon_mutation_requires_confirmation(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    # Setup session and canon entity
    client.post("/api/command", json={
        "action_id": "session.create",
        "idempotency_key": "sess-create-2",
        "payload": {"campaign_id": "default", "session_id": "session-2"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    })
    # create entity as canon provenance directly via API
    client.post("/api/command", json={
        "action_id": "entity.create",
        "idempotency_key": "canon-entity-create",
        "payload": {"entity_type": "character", "entity_id": "cant-1", "payload": {"name": "Queen"}, "provenance": "canon"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-2"},
    })

    # try update without confirm -> blocked
    update_resp = client.post("/api/command", json={
        "action_id": "entity.update",
        "idempotency_key": "canon-entity-update-1",
        "payload": {"entity_type": "character", "entity_id": "cant-1", "payload": {"name": "Queen II"}},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-2"},
    })
    assert update_resp.status_code == 412
    assert update_resp.get_json().get("reason_code") == "precondition.canon_mutation_confirmation_required"

    # confirm and retry update
    update_confirm = client.post("/api/command", json={
        "action_id": "entity.update",
        "idempotency_key": "canon-entity-update-2",
        "payload": {"entity_type": "character", "entity_id": "cant-1", "payload": {"name": "Queen II"}, "confirm": True},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-2"},
    })
    assert update_confirm.status_code == 200
    assert update_confirm.get_json().get("action_result", {}).get("payload", {}).get("name") == "Queen II"

    # delete without confirm blocked
    delete_resp = client.post("/api/command", json={
        "action_id": "entity.delete",
        "idempotency_key": "canon-entity-delete-1",
        "payload": {"entity_type": "character", "entity_id": "cant-1"},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-2"},
    })
    assert delete_resp.status_code == 412

    # delete with confirm passes
    delete_confirm = client.post("/api/command", json={
        "action_id": "entity.delete",
        "idempotency_key": "canon-entity-delete-2",
        "payload": {"entity_type": "character", "entity_id": "cant-1", "confirm": True},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "session-2"},
    })
    assert delete_confirm.status_code == 200
    assert delete_confirm.get_json().get("action_result", {}).get("status") == "deleted"


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


def test_precondition_campaign_session_mismatch_returns_412(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path, implicit_session_create=False)

    # Attempt command with non-existent campaign/session in strict mode path
    payload = {
        "action_id": "NO_OP_TEST",
        "idempotency_key": "mismatch-key",
        "metadata": {"login_id": "default", "campaign_id": "missing-camp", "session_id": "missing-sess"},
    }
    resp = client.post("/api/command", json=payload)
    assert resp.status_code == 412
    data = resp.get_json()
    assert data.get("reason_code") == "precondition.campaign_session_mismatch"


def test_session_create_with_foreign_campaign_returns_403(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    # seed campaign for different user
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO campaigns (login_id, campaign_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("other", "camp-x", "Other campaign", "active", "now", "now"),
    )
    conn.commit()
    conn.close()

    payload = {
        "action_id": "session.create",
        "idempotency_key": "sess-create-foreign",
        "payload": {"campaign_id": "camp-x", "session_id": "sess-fail"},
        "metadata": {"login_id": "default", "campaign_id": "camp-x", "session_id": "default"},
    }
    resp = client.post("/api/command", json=payload)
    assert resp.status_code == 403
    data = resp.get_json()
    assert data.get("reason_code") == "precondition.owner_scope_mismatch"


def test_session_events_persists_after_command(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    payload = {
        "action_id": "NO_OP_TEST",
        "idempotency_key": "events-key-1",
        "metadata": {"login_id": "default", "campaign_id": "camp-1", "session_id": "default"},
    }
    command_resp = client.post("/api/command", json=payload)
    assert command_resp.status_code == 200
    assert command_resp.get_json().get("status") == "ok"

    events_resp = client.get("/api/sessions/default/events", headers={"X-Login-Id": "default"})
    assert events_resp.status_code == 200
    events = events_resp.get_json().get("events", [])
    assert any(ev.get("idempotency_key") == "events-key-1" for ev in events)


def test_session_events_enforces_owner_scope(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    payload = {
        "action_id": "NO_OP_TEST",
        "idempotency_key": "events-key-2",
        "metadata": {"login_id": "default", "campaign_id": "camp-1", "session_id": "default"},
    }
    command_resp = client.post("/api/command", json=payload)
    assert command_resp.status_code == 200

    events_resp = client.get("/api/sessions/default/events", headers={"X-Login-Id": "other"})
    assert events_resp.status_code == 200
    events = events_resp.get_json().get("events", [])
    assert not any(ev.get("idempotency_key") == "events-key-2" for ev in events)

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
