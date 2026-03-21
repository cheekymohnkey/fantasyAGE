import os


def ensure_dir(path: str) -> None:
    """Create directory path if it doesn't exist (idempotent)."""
    os.makedirs(path, exist_ok=True)
