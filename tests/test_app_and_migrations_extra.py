import os
import sqlite3
import subprocess
import sys

import pytest

from backend import app as backend_app
from backend import command_service as cs
from backend import contracts as contracts_mod
from backend import migrations as migrations_mod


def _setup_temp_db(tmp_path):
    # reuse migration runner to create a working DB
    db_dir = tmp_path / "runtime"
    db_dir.mkdir()
    return str(db_dir / "session.db")


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


def test_list_migration_files_nonexistent_returns_empty():
    res = migrations_mod._list_migration_files("/this/path/does/not/exist")
    assert res == []


def test_run_migrations_with_empty_dir(tmp_path):
    db_path = str(tmp_path / "session.db")
    empty_dir = str(tmp_path / "migrations_empty")
    os.makedirs(empty_dir, exist_ok=True)

    # Should not raise and simply return when no .sql files
    migrations_mod.run_migrations(db_path, migrations_dir=empty_dir)


def test_run_migrations_with_invalid_sql_raises(tmp_path):
    db_path = str(tmp_path / "session.db")
    migrations_dir = str(tmp_path / "migrations_bad")
    os.makedirs(migrations_dir, exist_ok=True)
    bad_file = os.path.join(migrations_dir, "0009_bad.sql")
    with open(bad_file, "w", encoding="utf-8") as fh:
        fh.write("THIS IS NOT SQL;\n")

    with pytest.raises(sqlite3.DatabaseError):
        migrations_mod.run_migrations(db_path, migrations_dir=migrations_dir)


def test_apply_migration_creates_table_and_records_version(tmp_path):
    db_path = str(tmp_path / "session.db")
    migrations_dir = str(tmp_path / "migrations_ok")
    os.makedirs(migrations_dir, exist_ok=True)
    fname = "0003_create_foo.sql"
    path = os.path.join(migrations_dir, fname)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("CREATE TABLE foo (id INTEGER PRIMARY KEY);\nINSERT INTO foo (id) VALUES (1);\n")

    migrations_mod.run_migrations(db_path, migrations_dir=migrations_dir)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='foo'")
    assert cur.fetchone() is not None

    cur.execute("SELECT version FROM schema_migrations WHERE version=?", (fname,))
    assert cur.fetchone() is not None
    conn.close()


def _run_migrate_script(db_path):
    script = os.path.join(os.getcwd(), "work-process", "scripts", "migrate.py")
    migrations_dir = os.path.join(os.getcwd(), "work-process", "db", "migrations")
    ret = subprocess.run(
        [sys.executable, script, "--db", db_path, "--migrations", migrations_dir],
        capture_output=True,
        text=True,
    )
    assert ret.returncode == 0, f"Migrations failed: {ret.stderr}"


def test_load_default_login_id_returns_fallback(tmp_path):
    db_path = str(tmp_path / "session.db")
    # no migrations run -> no runtime_config table
    val = cs.load_default_login_id(db_path, fallback="fallback-id")
    assert val == "fallback-id"


def test_load_runtime_config_respects_default_login_id_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DEFAULT_LOGIN_ID", "env-default-login")
    runtime = backend_app.load_runtime_config(default_login_id="default")
    assert runtime.default_login_id == "env-default-login"


def test_ensure_owner_scoped_session_existing_session_mismatch(tmp_path):
    db_path = str(tmp_path / "session.db")
    _run_migrate_script(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # insert a session that belongs to a different login/campaign
    cur.execute(
        (
            "INSERT OR IGNORE INTO sessions (login_id, campaign_id, session_id, "
            "state_version, scene_mode, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ),
        ("other", "camp-x", "sess-1", 0, "default", "{}", "now"),
    )
    conn.commit()
    conn.close()

    cmd = contracts_mod.ParsedCommand(
        action_id="NO_OP",
        idempotency_key="k",
        payload={},
        context=contracts_mod.CommandContext(
            login_id="default",
            campaign_id="camp-1",
            session_id="sess-1",
            correlation_id="",
        ),
    )

    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(cs.OwnerScopeError):
            cs._ensure_owner_scoped_session(
                conn, cmd, created_at="now", implicit_session_create=True
            )
    finally:
        conn.close()


def test_ensure_owner_scoped_session_campaign_collision(tmp_path):
    db_path = str(tmp_path / "session.db")
    _run_migrate_script(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # insert a campaign owned by someone else
    cur.execute(
        (
            "INSERT OR IGNORE INTO campaigns (login_id, campaign_id, name, status, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
        ),
        ("other", "camp-1", "C", "active", "now", "now"),
    )
    conn.commit()
    conn.close()

    cmd = contracts_mod.ParsedCommand(
        action_id="NO_OP",
        idempotency_key="k",
        payload={},
        context=contracts_mod.CommandContext(
            login_id="default",
            campaign_id="camp-1",
            session_id="sess-9",
            correlation_id="",
        ),
    )

    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(cs.OwnerScopeError):
            cs._ensure_owner_scoped_session(
                conn, cmd, created_at="now", implicit_session_create=True
            )
    finally:
        conn.close()


def test_ensure_owner_scoped_session_strict_mode_raises(tmp_path):
    db_path = str(tmp_path / "session.db")
    _run_migrate_script(db_path)

    cmd = contracts_mod.ParsedCommand(
        action_id="NO_OP",
        idempotency_key="k",
        payload={},
        context=contracts_mod.CommandContext(
            login_id="default",
            campaign_id="camp-new",
            session_id="sess-new",
            correlation_id="",
        ),
    )

    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(cs.PreconditionError):
            cs._ensure_owner_scoped_session(
                conn, cmd, created_at="now", implicit_session_create=False
            )
    finally:
        conn.close()


def test_handle_command_returns_existing_canonical(tmp_path):
    db_path = str(tmp_path / "session.db")
    _run_migrate_script(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # create a session owned by default so ensure_owner_scoped_session passes
    cur.execute(
        (
            "INSERT OR IGNORE INTO sessions (login_id, campaign_id, session_id, "
            "state_version, scene_mode, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ),
        ("default", "camp-a", "sess-x", 0, "default", "{}", "now"),
    )
    # insert canonical JSON into command_receipts
    canonical = '{"status":"ok","action_id":"NO_OP","idempotency_key":"key-1","action_result":{}}'
    cur.execute(
        (
            "INSERT OR IGNORE INTO command_receipts (login_id, campaign_id, session_id, "
            "idempotency_key, action_id, action_result_json, correlation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        ("default", "camp-a", "sess-x", "key-1", "NO_OP", canonical, "", "now"),
    )
    conn.commit()
    conn.close()

    cmd = contracts_mod.ParsedCommand(
        action_id="NO_OP",
        idempotency_key="key-1",
        payload={},
        context=contracts_mod.CommandContext(
            login_id="default",
            campaign_id="camp-a",
            session_id="sess-x",
            correlation_id="",
        ),
    )

    resp = cs.handle_command(db_path, cmd, implicit_session_create=True)
    assert resp["idempotency_key"] == "key-1"


def test_handle_command_bad_existing_json_raises_persistence_error(tmp_path):
    db_path = str(tmp_path / "session.db")
    _run_migrate_script(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        (
            "INSERT OR IGNORE INTO sessions (login_id, campaign_id, session_id, "
            "state_version, scene_mode, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ),
        ("default", "camp-a", "sess-x", 0, "default", "{}", "now"),
    )
    cur.execute(
        (
            "INSERT OR IGNORE INTO command_receipts (login_id, campaign_id, session_id, "
            "idempotency_key, action_id, action_result_json, correlation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        ("default", "camp-a", "sess-x", "k-bad", "NO_OP", "not-json", "", "now"),
    )
    conn.commit()
    conn.close()

    cmd = contracts_mod.ParsedCommand(
        action_id="NO_OP",
        idempotency_key="k-bad",
        payload={},
        context=contracts_mod.CommandContext(
            login_id="default",
            campaign_id="camp-a",
            session_id="sess-x",
            correlation_id="",
        ),
    )

    with pytest.raises(cs.PersistenceError):
        cs.handle_command(db_path, cmd, implicit_session_create=True)


def test_handle_command_inserts_new_receipt(tmp_path):
    db_path = str(tmp_path / "session.db")
    _run_migrate_script(db_path)
    cmd = contracts_mod.ParsedCommand(
        action_id="NO_OP",
        idempotency_key="fresh-key",
        payload={},
        context=contracts_mod.CommandContext(
            login_id="default",
            campaign_id="default",
            session_id="default",
            correlation_id="corr-1",
        ),
    )

    resp = cs.handle_command(db_path, cmd, implicit_session_create=True)
    assert resp.get("idempotency_key") == "fresh-key"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT idempotency_key FROM command_receipts WHERE idempotency_key=?",
        ("fresh-key",),
    )
    assert cur.fetchone() is not None
    conn.close()



def test_command_invalid_json_returns_400(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    # send invalid JSON body
    resp = client.post("/api/command", data="not-json", content_type="application/json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("reason_code") == "validation.invalid_payload"


def test_command_empty_json_returns_400(tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    resp = client.post("/api/command", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("reason_code") == "validation.invalid_payload"


def test_list_sessions_db_error_returns_500(monkeypatch, tmp_path):
    db_path = _setup_temp_db(tmp_path)
    client = _build_client(db_path)

    # Monkeypatch db.connect to raise to exercise error branch
    import backend.db as backend_db


    def _bad_connect(_):
        raise RuntimeError("cannot connect")


    monkeypatch.setattr(backend_db, "connect", _bad_connect)

    resp = client.get("/api/sessions")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data.get("reason_code") == "internal.unable_list_sessions"


def test_app_error_handlers_return_expected_payload():
    from backend.errors import ValidationError

    err = ValidationError("bad", remediation_hint="hint", field="body")
    with backend_app.app.test_request_context():
        resp, status = backend_app.handle_app_error(err)
        assert status == 400
        assert resp.get_json()["reason_code"] == "validation.invalid_payload"

    # unexpected error handler
    with backend_app.app.test_request_context():
        resp2, status2 = backend_app.handle_unexpected_error(Exception("boom"))
        assert status2 == 500
        assert resp2.get_json()["reason_code"] == "internal.unhandled_exception"
