import logging
import os
import sqlite3
from collections.abc import Callable

from flask import Flask, jsonify, request
from flask_cors import CORS

from .command_service import (
    build_fallback_context,
    enforce_owner_scope,
    handle_command,
    load_default_login_id,
)
from .config import load_runtime_config
from .contracts import parse_command_payload
from .errors import AppError, ValidationError
from .migrations import run_migrations

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger("backend")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "backend_requests.log")
    try:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        logger.exception("Failed to create file handler for logging")

    return logger


logger = _configure_logger()
runtime = load_runtime_config()


def _bootstrap() -> None:
    global runtime
    try:
        run_migrations(runtime.db_path)
    except Exception:
        logger.exception("Migration runner failed during startup")

    default_login_id = load_default_login_id(runtime.db_path, runtime.default_login_id)
    runtime = load_runtime_config(default_login_id=default_login_id)
    logger.info(
        "Loaded runtime defaults login_id=%s db_path=%s", runtime.default_login_id, runtime.db_path
    )

    # Seed the default session so strict mode has a selectable session in early testing
    # Optional typed DB connect helper (imported if available)
    _db_connect: Callable[[str], sqlite3.Connection] | None = None
    try:
        from .db import connect as _db_connect
    except Exception:
        _db_connect = None
    try:
        # idempotent create of default campaign/session
        from .command_service import _utc_now
        conn = None
        try:
            from .db import connect as _connect
            conn = _connect(runtime.db_path)
            cur = conn.cursor()
            created_at = _utc_now()
            cur.execute(
                (
                    "INSERT OR IGNORE INTO campaigns (login_id, campaign_id, name, status, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (
                    runtime.default_login_id,
                    runtime.default_campaign_id,
                    "Default Campaign",
                    "active",
                    created_at,
                    created_at,
                ),
            )
            cur.execute(
                (
                    "INSERT OR IGNORE INTO sessions (login_id, campaign_id, "
                    "session_id, state_version, scene_mode, "
                    "payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
                ),
                (
                    runtime.default_login_id,
                    runtime.default_campaign_id,
                    runtime.default_session_id,
                    0,
                    "default",
                    "{}",
                    created_at,
                ),
            )
            conn.commit()
            logger.info(
                "Seeded default session campaign=%s session=%s",
                runtime.default_campaign_id,
                runtime.default_session_id,
            )
        finally:
            if conn:
                conn.close()
    except Exception:
        logger.exception("Failed to seed default session during bootstrap")


_bootstrap()


@app.post("/api/command")
def command():
    try:
        data = request.get_json(silent=False)
    except Exception as err:
        raise ValidationError(
            "Invalid JSON payload",
            remediation_hint="Send a valid JSON object in the request body.",
            field="body",
        ) from err

    if not data:
        raise ValidationError(
            "Empty JSON payload",
            remediation_hint="Send a JSON object with action_id and idempotency_key.",
            field="body",
        )

    fallback_context = build_fallback_context(
        default_login_id=runtime.default_login_id,
        default_campaign_id=runtime.default_campaign_id,
        default_session_id=runtime.default_session_id,
    )
    parsed = parse_command_payload(data, fallback_context)
    enforce_owner_scope(request.headers.get("X-Login-Id"), parsed)

    response = handle_command(runtime.db_path, parsed, runtime.implicit_session_create)
    log_template = (
        "event=command_handled correlation_id=%s action_id=%s "
        "session_id=%s command_type=%s outcome=%s"
    )
    logger.info(
        log_template,
        parsed.context.correlation_id,
        parsed.action_id,
        parsed.context.session_id,
        parsed.action_id,
        response.get("status", "ok"),
    )
    return jsonify(response)


@app.get("/api/sessions")
def list_sessions():
    try:
        from .db import connect as _connect

        conn = _connect(runtime.db_path)
        cur = conn.cursor()
        cur.execute(
            (
                "SELECT session_id, campaign_id, login_id, updated_at "
                "FROM sessions WHERE login_id=? ORDER BY updated_at DESC"
            ),
            (runtime.default_login_id,),
        )
        rows = cur.fetchall()
        sessions = [
            {"session_id": r[0], "campaign_id": r[1], "login_id": r[2], "updated_at": r[3]}
            for r in rows
        ]
        return jsonify({"status": "ok", "sessions": sessions})
    except Exception:
        logger.exception("Failed to list sessions")
        payload = {
            "status": "error",
            "reason_code": "internal.unable_list_sessions",
            "message": "Unable to list sessions",
            "remediation_hint": "Check backend logs",
        }
        return jsonify(payload), 500
    finally:
        try:
            if "conn" in locals() and conn:
                conn.close()
        except Exception:
            pass


@app.errorhandler(AppError)
def handle_app_error(err: AppError):
    logger.warning("event=app_error reason_code=%s message=%s", err.reason_code, err.message)
    return jsonify(err.to_dict()), err.status_code


@app.errorhandler(Exception)
def handle_unexpected_error(err: Exception):
    logger.exception("event=unexpected_error")
    payload = {
        "status": "error",
        "reason_code": "internal.unhandled_exception",
        "message": "Unexpected internal error",
        "remediation_hint": "Retry request; if issue persists inspect backend logs.",
    }
    return jsonify(payload), 500


if __name__ == "__main__":
    logger.info("Starting backend on 0.0.0.0:8000, DB=%s", runtime.db_path)
    app.run(host="0.0.0.0", port=8000)
