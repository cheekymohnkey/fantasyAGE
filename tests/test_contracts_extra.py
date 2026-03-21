import pytest

from backend.contracts import (
    parse_command_payload,
    _require_non_empty_string,
    CommandContext,
    ParsedCommand,
)
from backend.errors import ValidationError


def test_require_non_empty_string_strips_and_returns():
    assert _require_non_empty_string("  abc  ", "field") == "abc"


def test_require_non_empty_string_raises_on_empty():
    with pytest.raises(ValidationError) as exc:
        _require_non_empty_string("   ", "myfield")
    assert exc.value.field == "myfield"


def test_parse_command_payload_rejects_non_dict():
    fallback = CommandContext("d", "c", "s", "corr")
    with pytest.raises(ValidationError):
        parse_command_payload("not-a-dict", fallback)


def test_parse_command_payload_empty_action_or_idempotency_raises():
    fallback = CommandContext("d", "c", "s", "")
    with pytest.raises(ValidationError):
        parse_command_payload({"action_id": "", "idempotency_key": "k"}, fallback)
    with pytest.raises(ValidationError):
        parse_command_payload({"action_id": "A", "idempotency_key": ""}, fallback)


def test_parse_command_payload_invalid_payload_and_metadata_types():
    fallback = CommandContext("d", "c", "s", "")
    with pytest.raises(ValidationError) as e1:
        parse_command_payload({"action_id": "A", "idempotency_key": "k", "payload": "no"}, fallback)
    assert e1.value.field == "payload"

    with pytest.raises(ValidationError) as e2:
        parse_command_payload({"action_id": "A", "idempotency_key": "k", "metadata": "no"}, fallback)
    assert e2.value.field == "metadata"


def test_parse_command_payload_uses_fallback_and_metadata_overrides():
    fallback = CommandContext("fallback-login", "fallback-camp", "fallback-sess", "fb-corr")
    raw = {
        "action_id": "ACT",
        "idempotency_key": "id-1",
        # metadata missing login/campaign/session -> should use fallback
    }
    parsed = parse_command_payload(raw, fallback)
    assert isinstance(parsed, ParsedCommand)
    assert parsed.context.login_id == "fallback-login"
    assert parsed.context.campaign_id == "fallback-camp"

    # metadata overrides
    raw2 = {
        "action_id": "ACT",
        "idempotency_key": "id-2",
        "metadata": {"login_id": "alice", "campaign_id": "camp-x", "session_id": "sess-y"},
    }
    parsed2 = parse_command_payload(raw2, fallback)
    assert parsed2.context.login_id == "alice"
    assert parsed2.context.campaign_id == "camp-x"
    assert parsed2.context.session_id == "sess-y"


def test_parse_command_payload_correlation_id_selection():
    fallback = CommandContext("d", "c", "s", "fallback-corr")
    raw = {"action_id": "A", "idempotency_key": "k", "correlation_id": "raw-corr"}
    parsed = parse_command_payload(raw, fallback)
    assert parsed.context.correlation_id == "raw-corr"

    raw2 = {"action_id": "A", "idempotency_key": "k", "metadata": {"correlation_id": "meta-corr"}}
    parsed2 = parse_command_payload(raw2, fallback)
    assert parsed2.context.correlation_id == "meta-corr"
