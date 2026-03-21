import json
from typing import Any


def safe_dumps(obj: Any) -> str:
    """Serialize to compact JSON suitable for storage/logging.

    Uses compact separators to keep stored payloads consistent.
    """
    return json.dumps(obj, separators=(",", ":"))


def safe_loads(s: str) -> Any:
    """Load JSON string to Python object, raising on error."""
    return json.loads(s)
