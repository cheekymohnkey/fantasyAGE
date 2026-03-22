import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    db_path: str
    default_login_id: str
    default_campaign_id: str
    default_session_id: str
    implicit_session_create: bool


DEFAULT_DB_PATH = os.path.join("work-process", "runtime", "session.db")


def load_runtime_config(default_login_id: str = "default") -> RuntimeConfig:
    env_login_id = os.environ.get("DEFAULT_LOGIN_ID")
    if isinstance(env_login_id, str) and env_login_id.strip():
        default_login_id = env_login_id.strip()

    return RuntimeConfig(
        db_path=os.environ.get("SESSION_DB", DEFAULT_DB_PATH),
        default_login_id=default_login_id,
        default_campaign_id=os.environ.get("DEFAULT_CAMPAIGN_ID", "default"),
        default_session_id=os.environ.get("DEFAULT_SESSION_ID", "default"),
        implicit_session_create=(
            os.environ.get("IMPLICIT_SESSION_CREATE", "false").lower()
            in ("1", "true", "yes")
        ),
    )
