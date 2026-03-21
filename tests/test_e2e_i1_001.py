import os
import sqlite3
import subprocess
import tempfile


def test_e2e_i1_001_command_roundtrip():
    migrate_script = os.path.join(os.getcwd(), "work-process", "scripts", "migrate.py")
    migrations_dir = os.path.join(os.getcwd(), "work-process", "db", "migrations")

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "session.db")

        # Run migrations to temp DB
        r = subprocess.run(
            [
                __import__("sys").executable,
                migrate_script,
                "--db",
                db_path,
                "--migrations",
                migrations_dir,
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"Migrate failed: {r.stderr}"

        # set env so backend runtime picks this DB
        os.environ["SESSION_DB"] = db_path

        # import backend app after env set and use Flask test client for HTTP-like roundtrip
        import importlib

        backend = importlib.import_module("backend.app")
        backend.app.config["TESTING"] = True
        # ensure backend runtime uses our temp DB path
        backend.runtime = backend.load_runtime_config(default_login_id="default")
        backend.runtime = backend.runtime.__class__(
            db_path=db_path,
            default_login_id=backend.runtime.default_login_id,
            default_campaign_id=backend.runtime.default_campaign_id,
            default_session_id=backend.runtime.default_session_id,
            implicit_session_create=True,
        )

        payload = {
            "action_id": "E2E_NOOP",
            "idempotency_key": "e2e-1-xyz",
            "metadata": {"login_id": "default", "campaign_id": "camp-1", "session_id": "sess-1"},
        }
        with backend.app.test_client() as client:
            resp = client.post("/api/command", json=payload)
            assert resp.status_code == 200
            j = resp.get_json()
            assert j.get("status") == "ok"

        # verify DB
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT action_id FROM command_receipts WHERE idempotency_key=?", ("e2e-1-xyz",)
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None and row[0] == "E2E_NOOP"
