-- 0002_runtime_config_default_login.sql
PRAGMA foreign_keys = ON;

-- Seed a default login id for v1 apps. Update as needed by ops.
INSERT INTO runtime_config (config_key, config_value, updated_at)
VALUES ('default_login_id', 'default', datetime('now'))
ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=excluded.updated_at;
