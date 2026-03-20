import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, cast

from .contracts import CommandContext, ParsedCommand
from .db import connect, transaction
from .errors import OwnerScopeError, PersistenceError


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_default_login_id(db_path: str, fallback: str = "default") -> str:
    conn = connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT config_value FROM runtime_config WHERE config_key='default_login_id'")
        row = cur.fetchone()
        if row and row[0]:
            return str(row[0])
    except Exception:
        return fallback
    finally:
        conn.close()
    return fallback


def build_fallback_context(
    default_login_id: str, default_campaign_id: str, default_session_id: str
) -> CommandContext:
    return CommandContext(
        login_id=default_login_id,
        campaign_id=default_campaign_id,
        session_id=default_session_id,
        correlation_id="",
    )


def enforce_owner_scope(header_login_id: str | None, command: ParsedCommand) -> None:
    if (
        header_login_id
        and header_login_id.strip()
        and header_login_id.strip() != command.context.login_id
    ):
        raise OwnerScopeError(
            message="Header login_id does not match command metadata login_id",
            remediation_hint=(
                "Use matching login scope values or omit metadata.login_id "
                "to use the default."
            ),
        )


def _ensure_owner_scoped_session(conn, command: ParsedCommand, created_at: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT login_id, campaign_id FROM sessions WHERE session_id=?",
        (command.context.session_id,),
    )
    existing_session = cur.fetchone()
    if existing_session:
        if (
            existing_session[0] != command.context.login_id
            or existing_session[1] != command.context.campaign_id
        ):
            raise OwnerScopeError(
                message="session_id already exists under different owner scope",
                remediation_hint="Use a session_id owned by the current login/campaign scope.",
            )

    cur.execute(
        "SELECT login_id FROM campaigns WHERE campaign_id=?", (command.context.campaign_id,)
    )
    existing_campaign = cur.fetchone()
    if existing_campaign and existing_campaign[0] != command.context.login_id:
        raise OwnerScopeError(
            message="campaign_id already exists under different login scope",
            remediation_hint="Use a campaign_id owned by the current login scope.",
        )

    cur.execute(
        """INSERT OR IGNORE INTO campaigns
        (login_id, campaign_id, name, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            command.context.login_id,
            command.context.campaign_id,
            "Default Campaign",
            "active",
            created_at,
            created_at,
        ),
    )
    cur.execute(
        """INSERT OR IGNORE INTO sessions
        (login_id, campaign_id, session_id, state_version, scene_mode, payload_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            command.context.login_id,
            command.context.campaign_id,
            command.context.session_id,
            0,
            "default",
            "{}",
            created_at,
        ),
    )


def _response_payload(command: ParsedCommand) -> dict:
    return {
        "status": "ok",
        "action_id": command.action_id,
        "action": command.action_id,
        "idempotency_key": command.idempotency_key,
        "idempotency": command.idempotency_key,
        "action_result": {},
        "action_result_json": "{}",
        "event": None,
        "context": asdict(command.context),
    }


def handle_command(db_path: str, command: ParsedCommand) -> dict:
    created_at = _utc_now()

    try:
        with transaction(db_path) as conn:
            cur = conn.cursor()
            _ensure_owner_scoped_session(conn, command, created_at)

            cur.execute(
                """SELECT action_result_json FROM command_receipts
                WHERE login_id=? AND campaign_id=? AND session_id=? AND idempotency_key=?""",
                (
                    command.context.login_id,
                    command.context.campaign_id,
                    command.context.session_id,
                    command.idempotency_key,
                ),
            )
            existing = cur.fetchone()
            if existing:
                try:
                    parsed_existing = cast(dict[str, Any], json.loads(existing[0]))
                    return parsed_existing
                except Exception as err:
                    raise PersistenceError(
                        message="Stored idempotent result is unreadable",
                        remediation_hint=(
                            "Inspect command_receipts rows for malformed "
                            "action_result_json."
                        ),
                    ) from err

            response = _response_payload(command)
            response_json = json.dumps(response, separators=(",", ":"))

            cur.execute(
                """INSERT INTO command_receipts
                (login_id, campaign_id, session_id, idempotency_key, action_id,
                action_result_json, correlation_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    command.context.login_id,
                    command.context.campaign_id,
                    command.context.session_id,
                    command.idempotency_key,
                    command.action_id,
                    response_json,
                    command.context.correlation_id,
                    created_at,
                ),
            )
            return response
    except OwnerScopeError:
        raise
    except Exception as exc:
        raise PersistenceError(message=f"Failed to persist command receipt: {exc}") from exc
