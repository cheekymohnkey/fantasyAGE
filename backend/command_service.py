import json
import sqlite3
from dataclasses import asdict
from typing import Any, cast

from .contracts import CommandContext, ParsedCommand
from .db import connect, transaction
from .errors import AppError, OwnerScopeError, PersistenceError, PreconditionError, ValidationError
from .timeutils import utc_now_z


def _utc_now() -> str:
    return utc_now_z()


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


def _ensure_owner_scoped_session(
    conn,
    command: ParsedCommand,
    created_at: str,
    implicit_session_create: bool,
) -> None:
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
    # If session does not exist, decide between implicit create (dev/test) or strict enforcement
    if not existing_session:
        # check campaign ownership collision
        cur.execute(
            "SELECT login_id FROM campaigns WHERE campaign_id=?", (command.context.campaign_id,)
        )
        existing_campaign = cur.fetchone()
        if existing_campaign and existing_campaign[0] != command.context.login_id:
            raise OwnerScopeError(
                message="campaign_id already exists under different login scope",
                remediation_hint="Use a campaign_id owned by the current login scope.",
            )

        if not implicit_session_create:
            # Strict mode: do not implicitly create sessions; require explicit selection
            raise PreconditionError(
                message="session_id does not exist",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint=(
                    "Select or create the session for the active campaign "
                    "before retrying."
                ),
            )

        # Implicit create path (idempotent)
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


def _resolve_campaign_id(command: ParsedCommand) -> str:
    campaign_id = command.payload.get("campaign_id", command.context.campaign_id)
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise ValidationError(
            "campaign_id must be a non-empty string",
            remediation_hint="Provide 'campaign_id' in payload or metadata for campaign commands.",
            field="payload.campaign_id",
        )
    return campaign_id.strip()


def _handle_campaign_command(conn, command: ParsedCommand, created_at: str) -> dict[str, Any]:
    action = command.action_id
    login_id = command.context.login_id

    if action == "campaign.create":
        campaign_id = _resolve_campaign_id(command)
        name = command.payload.get("name", campaign_id)
        if not isinstance(name, str) or not name.strip():
            raise ValidationError(
                "name must be a non-empty string",
                remediation_hint="Provide 'name' for the campaign.",
                field="payload.name",
            )
        name = name.strip()

        cur = conn.cursor()
        cur.execute(
            "SELECT login_id, status, name, created_at FROM campaigns WHERE campaign_id=?",
            (campaign_id,),
        )
        existing = cur.fetchone()
        if existing:
            if existing[0] != login_id:
                raise OwnerScopeError(
                    message="campaign_id already exists under different login scope",
                    remediation_hint="Use a campaign_id owned by the current login scope.",
                )
            return {
                "campaign_id": campaign_id,
                "name": existing[2],
                "status": existing[1],
                "created_at": existing[3],
            }

        status = "active"
        cur.execute(
            "INSERT INTO campaigns (login_id, campaign_id, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (login_id, campaign_id, name, status, created_at, created_at),
        )
        return {
            "campaign_id": campaign_id,
            "name": name,
            "status": status,
            "created_at": created_at,
        }

    if action == "campaign.list":
        cur = conn.cursor()
        cur.execute(
            "SELECT campaign_id, name, status, created_at, updated_at FROM campaigns WHERE login_id=? ORDER BY updated_at DESC",
            (login_id,),
        )
        rows = cur.fetchall()
        campaigns = [
            {
                "campaign_id": r[0],
                "name": r[1],
                "status": r[2],
                "created_at": r[3],
                "updated_at": r[4],
            }
            for r in rows
        ]
        return {"campaigns": campaigns}

    if action == "campaign.open":
        campaign_id = _resolve_campaign_id(command)
        cur = conn.cursor()
        cur.execute(
            "SELECT campaign_id, name, status, created_at, updated_at, login_id FROM campaigns WHERE campaign_id=?",
            (campaign_id,),
        )
        row = cur.fetchone()
        if not row:
            raise PreconditionError(
                message="campaign_id does not exist",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint="Create or select a valid campaign_id before opening.",
            )
        if row[5] != login_id:
            raise OwnerScopeError(
                message="campaign_id exists under different login scope",
                remediation_hint="Use a campaign_id owned by the current login scope.",
            )
        if row[2] != "active":
            raise PreconditionError(
                message="campaign is not active",
                remediation_hint="Only active campaigns can be opened.",
            )
        return {
            "campaign_id": row[0],
            "name": row[1],
            "status": row[2],
            "created_at": row[3],
            "updated_at": row[4],
        }

    if action == "campaign.archive":
        campaign_id = _resolve_campaign_id(command)
        cur = conn.cursor()
        cur.execute(
            "SELECT login_id FROM campaigns WHERE campaign_id=?",
            (campaign_id,),
        )
        row = cur.fetchone()
        if not row:
            raise PreconditionError(
                message="campaign_id does not exist",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint="Create or select a valid campaign_id before archiving.",
            )
        if row[0] != login_id:
            raise OwnerScopeError(
                message="campaign_id exists under different login scope",
                remediation_hint="Use a campaign_id owned by the current login scope.",
            )

        cur.execute(
            "UPDATE campaigns SET status=?, updated_at=? WHERE campaign_id=?",
            ("archived", created_at, campaign_id),
        )
        return {"campaign_id": campaign_id, "status": "archived", "updated_at": created_at}

    raise ValidationError(
        f"Unsupported campaign action: {action}",
        remediation_hint="Use campaign.create, campaign.list, campaign.open, or campaign.archive.",
    )


def _resolve_session_id(command: ParsedCommand) -> str:
    session_id = command.payload.get("session_id", command.context.session_id)
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValidationError(
            "session_id must be a non-empty string",
            remediation_hint="Provide 'session_id' in payload or metadata for session commands.",
            field="payload.session_id",
        )
    return session_id.strip()


def _handle_session_command(conn, command: ParsedCommand, created_at: str) -> dict[str, Any]:
    action = command.action_id
    login_id = command.context.login_id
    campaign_id = command.payload.get("campaign_id", command.context.campaign_id)
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise ValidationError(
            "campaign_id must be a non-empty string",
            remediation_hint="Provide 'campaign_id' in payload or metadata for session commands.",
            field="payload.campaign_id",
        )
    campaign_id = campaign_id.strip()

    # Verify campaign exists and is owned by current login
    cur = conn.cursor()
    cur.execute("SELECT login_id FROM campaigns WHERE campaign_id=?", (campaign_id,))
    row = cur.fetchone()
    if not row:
        raise PreconditionError(
            message="campaign_id does not exist",
            reason_code="precondition.campaign_session_mismatch",
            remediation_hint="Create or select a valid campaign before creating/listing/opening sessions.",
        )
    if row[0] != login_id:
        raise OwnerScopeError(
            message="campaign_id exists under different login scope",
            remediation_hint="Use a campaign_id owned by the current login scope.",
        )

    if action == "session.create":
        session_id = _resolve_session_id(command)
        cur.execute(
            "SELECT login_id, campaign_id FROM sessions WHERE session_id=?",
            (session_id,),
        )
        existing = cur.fetchone()
        if existing:
            if existing[0] != login_id or existing[1] != campaign_id:
                raise OwnerScopeError(
                    message="session_id already exists under different owner scope",
                    remediation_hint="Use a session_id owned by the current login/campaign scope.",
                )
            return {"session_id": session_id, "campaign_id": campaign_id}

        cur.execute(
            "INSERT INTO sessions (login_id, campaign_id, session_id, state_version, scene_mode, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (login_id, campaign_id, session_id, 0, "default", "{}", created_at),
        )
        return {"session_id": session_id, "campaign_id": campaign_id, "created_at": created_at}

    if action == "session.list":
        cur.execute(
            "SELECT session_id, campaign_id, updated_at FROM sessions WHERE login_id=? AND campaign_id=? ORDER BY updated_at DESC",
            (login_id, campaign_id),
        )
        rows = cur.fetchall()
        sessions = [
            {"session_id": r[0], "campaign_id": r[1], "updated_at": r[2]} for r in rows
        ]
        return {"sessions": sessions}

    if action == "session.open":
        session_id = _resolve_session_id(command)
        cur.execute(
            "SELECT login_id, campaign_id, session_id, updated_at FROM sessions WHERE session_id=?",
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            raise PreconditionError(
                message="session_id does not exist",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint="Create or select a valid session before opening.",
            )
        if row[0] != login_id or row[1] != campaign_id:
            raise OwnerScopeError(
                message="session_id exists under different owner scope",
                remediation_hint="Use a session_id owned by the current login/campaign scope.",
            )
        return {"session_id": row[2], "campaign_id": row[1], "updated_at": row[3]}

    raise ValidationError(
        f"Unsupported session action: {action}",
        remediation_hint="Use session.create, session.list, or session.open.",
    )


def _resolve_entity_key(command: ParsedCommand) -> tuple[str, str]:
    entity_type = command.payload.get("entity_type")
    entity_id = command.payload.get("entity_id")
    if not isinstance(entity_type, str) or not entity_type.strip():
        raise ValidationError(
            "entity_type must be a non-empty string",
            remediation_hint="Provide 'entity_type' for entity commands.",
            field="payload.entity_type",
        )
    if not isinstance(entity_id, str) or not entity_id.strip():
        raise ValidationError(
            "entity_id must be a non-empty string",
            remediation_hint="Provide 'entity_id' for entity commands.",
            field="payload.entity_id",
        )
    return entity_type.strip(), entity_id.strip()


def _handle_entity_command(conn, command: ParsedCommand, created_at: str) -> dict[str, Any]:
    action = command.action_id
    login_id = command.context.login_id
    campaign_id = command.context.campaign_id
    session_id = command.context.session_id
    cur = conn.cursor()

    entity_type = None
    entity_id = None
    if action != "entity.list":
        entity_type, entity_id = _resolve_entity_key(command)

    if action == "entity.create":
        payload_json = json.dumps(command.payload.get("payload", {}), separators=(",", ":"))
        cur.execute(
            "SELECT is_deleted FROM session_entities WHERE session_id=? AND entity_type=? AND entity_id=?",
            (session_id, entity_type, entity_id),
        )
        existing = cur.fetchone()
        if existing:
            # idempotent: if already exists and not deleted, return current
            if existing[0] == 0:
                return {"entity_type": entity_type, "entity_id": entity_id, "payload": json.loads(payload_json)}
            # resurrect soft-deleted entity
            cur.execute(
                "UPDATE session_entities SET is_deleted=0, payload_json=?, updated_at=? WHERE session_id=? AND entity_type=? AND entity_id=?",
                (payload_json, created_at, session_id, entity_type, entity_id),
            )
            return {"entity_type": entity_type, "entity_id": entity_id, "payload": json.loads(payload_json), "status": "restored"}

        cur.execute(
            "INSERT INTO session_entities (login_id, campaign_id, session_id, entity_type, entity_id, provenance, is_deleted, payload_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (login_id, campaign_id, session_id, entity_type, entity_id, "campaign", 0, payload_json, created_at),
        )
        return {"entity_type": entity_type, "entity_id": entity_id, "payload": json.loads(payload_json)}

    if action == "entity.read":
        cur.execute(
            "SELECT is_deleted, payload_json FROM session_entities WHERE session_id=? AND entity_type=? AND entity_id=?",
            (session_id, entity_type, entity_id),
        )
        row = cur.fetchone()
        if not row or row[0] == 1:
            raise PreconditionError(
                message="Entity not found",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint="Ensure entity exists in the current session and campaign.",
            )
        return {"entity_type": entity_type, "entity_id": entity_id, "payload": json.loads(row[1])}

    if action == "entity.list":
        cur.execute(
            "SELECT entity_type, entity_id, payload_json, updated_at FROM session_entities WHERE login_id=? AND campaign_id=? AND session_id=? AND is_deleted=0 ORDER BY updated_at DESC",
            (login_id, campaign_id, session_id),
        )
        rows = cur.fetchall()
        entities = [
            {
                "entity_type": r[0],
                "entity_id": r[1],
                "payload": json.loads(r[2]),
                "updated_at": r[3],
            }
            for r in rows
        ]
        return {"entities": entities}

    if action == "entity.update":
        payload_json = json.dumps(command.payload.get("payload", {}), separators=(",", ":"))
        cur.execute(
            "SELECT is_deleted FROM session_entities WHERE session_id=? AND entity_type=? AND entity_id=?",
            (session_id, entity_type, entity_id),
        )
        row = cur.fetchone()
        if not row or row[0] == 1:
            raise PreconditionError(
                message="Entity not found or deleted",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint="Entity must exist and not be deleted to update.",
            )
        cur.execute(
            "UPDATE session_entities SET payload_json=?, updated_at=? WHERE session_id=? AND entity_type=? AND entity_id=?",
            (payload_json, created_at, session_id, entity_type, entity_id),
        )
        return {"entity_type": entity_type, "entity_id": entity_id, "payload": json.loads(payload_json)}

    if action == "entity.delete":
        cur.execute(
            "SELECT is_deleted FROM session_entities WHERE session_id=? AND entity_type=? AND entity_id=?",
            (session_id, entity_type, entity_id),
        )
        row = cur.fetchone()
        if not row:
            raise PreconditionError(
                message="Entity not found",
                reason_code="precondition.campaign_session_mismatch",
                remediation_hint="Entity must exist to delete.",
            )
        if row[0] == 1:
            return {"entity_type": entity_type, "entity_id": entity_id, "status": "already_deleted"}

        cur.execute(
            "UPDATE session_entities SET is_deleted=1, updated_at=? WHERE session_id=? AND entity_type=? AND entity_id=?",
            (created_at, session_id, entity_type, entity_id),
        )
        return {"entity_type": entity_type, "entity_id": entity_id, "status": "deleted"}

    raise ValidationError(
        f"Unsupported entity action: {action}",
        remediation_hint="Use entity.create, entity.read, entity.list, entity.update, or entity.delete.",
    )


def _response_payload(command: ParsedCommand, action_result: dict[str, Any] | None = None) -> dict:
    if action_result is None:
        action_result = {}
    action_result_json = json.dumps(action_result, separators=(",", ":"))
    return {
        "status": "ok",
        "action_id": command.action_id,
        "action": command.action_id,
        "idempotency_key": command.idempotency_key,
        "idempotency": command.idempotency_key,
        "action_result": action_result,
        "action_result_json": action_result_json,
        "event": None,
        "context": asdict(command.context),
    }


def _is_canonical_response(payload: dict[str, Any]) -> bool:
    required = {"status", "action_id", "idempotency_key", "action_result"}
    return required.issubset(set(payload.keys()))


def handle_command(
    db_path: str,
    command: ParsedCommand,
    implicit_session_create: bool = True,
) -> dict:
    created_at = _utc_now()

    try:
        with transaction(db_path) as conn:
            cur = conn.cursor()
            _ensure_owner_scoped_session(conn, command, created_at, implicit_session_create)

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
                    if _is_canonical_response(parsed_existing):
                        return parsed_existing
                    # Backward compatibility: older receipts stored '{}' only.
                    response = _response_payload(command)
                    response_json = json.dumps(response, separators=(",", ":"))
                    cur.execute(
                        (
                            """UPDATE command_receipts
                            SET action_id=?, action_result_json=?, correlation_id=?
                            WHERE login_id=? AND campaign_id=? AND
                            session_id=? AND idempotency_key=?"""
                        ),
                        (
                            command.action_id,
                            response_json,
                            command.context.correlation_id,
                            command.context.login_id,
                            command.context.campaign_id,
                            command.context.session_id,
                            command.idempotency_key,
                        ),
                    )
                    return response
                except Exception as err:
                    raise PersistenceError(
                        message="Stored idempotent result is unreadable",
                        remediation_hint=(
                            "Inspect command_receipts rows for malformed "
                            "action_result_json."
                        ),
                    ) from err

            action_result = {}
            if command.action_id.startswith("campaign."):
                action_result = _handle_campaign_command(conn, command, created_at)
            elif command.action_id.startswith("session."):
                action_result = _handle_session_command(conn, command, created_at)
            elif command.action_id.startswith("entity."):
                action_result = _handle_entity_command(conn, command, created_at)

            response = _response_payload(command, action_result)
            response_json = json.dumps(response, separators=(",", ":"))
            try:
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
            except sqlite3.IntegrityError as ie:
                # Likely a missing referenced session/campaign (FK failure).
                raise PreconditionError(
                    message=(
                        "Referenced campaign or session does not exist; "
                        "unable to persist command receipt"
                    ),
                    reason_code="precondition.campaign_session_mismatch",
                    remediation_hint=(
                        "Ensure the session and campaign exist for the provided metadata, "
                        "or enable implicit session creation in runtime config."
                    ),
                ) from ie
            return response
    except AppError:
        raise
    except NameError as ne:
        # Convert unexpected NameError into a clearer persistence error so logs surface
        # the missing symbol and a hint for maintainers to inspect imports.
        raise PersistenceError(
            message=(
                f"Internal name error while persisting command receipt: {ne}. "
                "Check backend imports and symbol availability."
            )
        ) from ne
    except Exception as exc:
        raise PersistenceError(message=f"Failed to persist command receipt: {exc}") from exc
