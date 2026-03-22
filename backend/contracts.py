import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft7Validator

from .errors import ValidationError


@dataclass(frozen=True)
class CommandContext:
    login_id: str
    campaign_id: str
    session_id: str
    correlation_id: str


@dataclass(frozen=True)
class ParsedCommand:
    action_id: str
    idempotency_key: str
    payload: dict[str, Any]
    context: CommandContext


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"{field_name} must be a non-empty string",
            remediation_hint=f"Provide '{field_name}' as a non-empty string.",
            field=field_name,
        )
    return value.strip()


def _load_api_command_schema() -> dict[str, Any]:
    schema_path = Path(__file__).resolve().parents[1] / "work-process" / "schemas" / "api_command.schema.json"
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as err:
        raise ValidationError(
            "API command schema not found",
            remediation_hint="Ensure api_command.schema.json exists in work-process/schemas.",
        ) from err


def _validate_api_command(raw: dict[str, Any]) -> None:
    schema = _load_api_command_schema()
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda e: e.path)
    if errors:
        first_err = errors[0]
        field_path = ".".join(str(p) for p in first_err.absolute_path) if first_err.absolute_path else "body"
        raise ValidationError(
            f"Invalid command payload: {first_err.message}",
            remediation_hint="Fix request body to match API command schema.",
            field=field_path,
        )


def parse_command_payload(raw: dict[str, Any], fallback_context: CommandContext) -> ParsedCommand:
    if not isinstance(raw, dict):
        raise ValidationError("Request body must be a JSON object")

    _validate_api_command(raw)

    action_id = _require_non_empty_string(raw.get("action_id", "NO_OP"), "action_id")
    idempotency_key = _require_non_empty_string(raw.get("idempotency_key", ""), "idempotency_key")

    payload = raw.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValidationError(
            "payload must be an object",
            remediation_hint="Send 'payload' as a JSON object.",
            field="payload",
        )

    metadata = raw.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValidationError(
            "metadata must be an object",
            remediation_hint="Send 'metadata' as a JSON object.",
            field="metadata",
        )

    login_id = metadata.get("login_id", fallback_context.login_id)
    campaign_id = metadata.get("campaign_id", fallback_context.campaign_id)
    session_id = metadata.get("session_id", fallback_context.session_id)
    correlation_id = raw.get(
        "correlation_id", metadata.get("correlation_id", fallback_context.correlation_id)
    )

    context = CommandContext(
        login_id=_require_non_empty_string(login_id, "metadata.login_id"),
        campaign_id=_require_non_empty_string(campaign_id, "metadata.campaign_id"),
        session_id=_require_non_empty_string(session_id, "metadata.session_id"),
        correlation_id=str(correlation_id or "").strip(),
    )

    return ParsedCommand(
        action_id=action_id,
        idempotency_key=idempotency_key,
        payload=payload,
        context=context,
    )
