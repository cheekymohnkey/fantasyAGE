-- 0001_initial.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
  login_id TEXT NOT NULL,
  campaign_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  login_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  session_id TEXT PRIMARY KEY,
  state_version INTEGER NOT NULL,
  scene_mode TEXT NOT NULL,
  round INTEGER,
  turn_index INTEGER,
  active_actor_id TEXT,
  payload_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_entities (
  login_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  provenance TEXT NOT NULL DEFAULT 'campaign',
  is_deleted INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (session_id, entity_type, entity_id),
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_events (
  event_id TEXT PRIMARY KEY,
  login_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  pre_version INTEGER NOT NULL,
  post_version INTEGER NOT NULL,
  action_id TEXT,
  payload_json TEXT NOT NULL,
  citations_json TEXT NOT NULL,
  correlation_id TEXT,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS confirmations (
  confirmation_id TEXT PRIMARY KEY,
  login_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  action_id TEXT NOT NULL,
  required INTEGER NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL,
  dm_actor TEXT,
  decided_at TEXT
);

CREATE TABLE IF NOT EXISTS command_receipts (
  login_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  action_id TEXT NOT NULL,
  action_result_json TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (login_id, campaign_id, session_id, idempotency_key),
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entity_mutation_warnings (
  warning_id TEXT PRIMARY KEY,
  login_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  provenance TEXT NOT NULL,
  operation TEXT NOT NULL,
  warning_message TEXT NOT NULL,
  acknowledged INTEGER NOT NULL,
  acknowledged_by TEXT,
  acknowledged_at TEXT,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS runtime_config (
  config_key TEXT PRIMARY KEY,
  config_value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_campaigns_owner
ON campaigns(login_id, status, updated_at);

CREATE INDEX IF NOT EXISTS idx_sessions_campaign
ON sessions(campaign_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_sessions_owner_campaign
ON sessions(login_id, campaign_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_events_session_time
ON session_events(session_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_events_action
ON session_events(action_id);

CREATE INDEX IF NOT EXISTS idx_entities_session_type
ON session_entities(session_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_confirmations_action
ON confirmations(action_id);

CREATE INDEX IF NOT EXISTS idx_entities_provenance
ON session_entities(session_id, provenance, entity_type);
