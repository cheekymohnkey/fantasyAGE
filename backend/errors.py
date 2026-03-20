from dataclasses import dataclass
from typing import Optional


@dataclass
class AppError(Exception):
    reason_code: str
    message: str
    status_code: int
    remediation_hint: str = ""
    field: Optional[str] = None

    def to_dict(self) -> dict:
        payload = {
            "status": "error",
            "reason_code": self.reason_code,
            "message": self.message,
        }
        if self.remediation_hint:
            payload["remediation_hint"] = self.remediation_hint
        if self.field:
            payload["field"] = self.field
        return payload


class ValidationError(AppError):
    def __init__(self, message: str, remediation_hint: str = "", field: Optional[str] = None):
        super().__init__(
            reason_code="validation.invalid_payload",
            message=message,
            status_code=400,
            remediation_hint=remediation_hint
            or "Send a valid command payload that matches the API contract.",
            field=field,
        )


class OwnerScopeError(AppError):
    def __init__(self, message: str, remediation_hint: str = ""):
        super().__init__(
            reason_code="precondition.owner_scope_mismatch",
            message=message,
            status_code=403,
            remediation_hint=remediation_hint
            or "Use a consistent login_id across headers, metadata, and persisted session scope.",
        )


class PersistenceError(AppError):
    def __init__(self, message: str, remediation_hint: str = ""):
        super().__init__(
            reason_code="persistence.transaction_failed",
            message=message,
            status_code=500,
            remediation_hint=remediation_hint
            or "Retry the request and check backend logs for transaction failures.",
        )
