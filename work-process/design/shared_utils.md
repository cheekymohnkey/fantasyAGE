# Shared Utilities Registry

This document lists project-wide shared utility functions and where to find them.

- **`utc_now_z()`**
  - Purpose: Return the current UTC timestamp as an ISO8601 string ending with `Z`.
  - Location: `backend/timeutils.py`
  - Signature: `def utc_now_z() -> str`
  - Example:
    ```py
    from backend.timeutils import utc_now_z

    ts = utc_now_z()  # e.g. "2026-03-21T09:00:00Z"
    ```
  - Notes: Use this helper for any database or audit timestamps to ensure consistent, timezone-aware formatting.

  - **`safe_dumps()` / `safe_loads()`**
    - Purpose: Consistent compact JSON serialization/deserialization for storage and receipts.
    - Location: `backend/jsonutils.py`
    - Signature: `def safe_dumps(obj: Any) -> str`, `def safe_loads(s: str) -> Any`
    - Example:
      ```py
      from backend.jsonutils import safe_dumps

      payload = {"a": 1}
      s = safe_dumps(payload)  # compact JSON
      ```

  - **`ensure_dir()`**
    - Purpose: Idempotent directory creation helper for logging and file-output paths.
    - Location: `backend/fsutils.py`
    - Signature: `def ensure_dir(path: str) -> None`
    - Example:
      ```py
      from backend.fsutils import ensure_dir

      ensure_dir("logs")
      ```

Guidelines
- Add new shared utilities to this registry when they are intended for use across multiple modules.
- Export stable, public helpers from `backend/__init__.py` to make discovery easier for contributors and tests.
- Document intended semantics, mutability, and whether the helper is part of the public API.
