from dataclasses import dataclass
from typing import Any

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


def parse_command_payload(raw: dict[str, Any], fallback_context: CommandContext) -> ParsedCommand:
    if not isinstance(raw, dict):
        raise ValidationError("Request body must be a JSON object")

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
