from backend import app as appmod


def test_command_invalid_json():
    client = appmod.app.test_client()
    # malformed JSON should trigger ValidationError with field 'body'
    rv = client.post("/api/command", data="{not-json", content_type="application/json")
    assert rv.status_code == 400
    payload = rv.get_json()
    assert payload["reason_code"] == "validation.invalid_payload"
    assert payload.get("field") == "body"


def test_command_empty_json():
    client = appmod.app.test_client()
    rv = client.post("/api/command", json={})
    assert rv.status_code == 400
    payload = rv.get_json()
    assert payload["reason_code"] == "validation.invalid_payload"
    assert payload.get("field") == "body"


def test_command_unexpected_exception(monkeypatch):
    client = appmod.app.test_client()

    def _boom(data, fallback_context):
        raise RuntimeError("boom")

    # monkeypatch parse_command_payload to raise an unexpected exception
    monkeypatch.setattr(appmod, "parse_command_payload", _boom)

    body = {
        "action_id": "NO_OP",
        "idempotency_key": "x",
        "payload": {},
        "metadata": {"login_id": "default", "campaign_id": "default", "session_id": "default"},
    }
    rv = client.post("/api/command", json=body)
    assert rv.status_code == 500
    payload = rv.get_json()
    assert payload["reason_code"] == "internal.unhandled_exception"


def test_list_sessions_db_error(monkeypatch, tmp_path):
    client = appmod.app.test_client()

    def _fail(db_path):
        raise Exception("no db")

    # replace backend.db.connect to force an error path
    import backend.db as backend_db

    monkeypatch.setattr(backend_db, "connect", _fail)

    rv = client.get("/api/sessions")
    assert rv.status_code == 500
    payload = rv.get_json()
    assert payload["reason_code"] == "internal.unable_list_sessions"
