from datetime import datetime, timezone


def utc_now_z() -> str:
    """Return current UTC time as ISO8601 string ending with 'Z'."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
