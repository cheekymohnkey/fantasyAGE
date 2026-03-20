# Fantasy AGE DM Assistant - Data Model v1

## 1) Purpose

This document defines canonical data contracts, validation rules, and persistence structures for v1.

Design principles:
- Event-sourced auditability with snapshot convenience.
- Deterministic mutation contracts for all mechanical outcomes.
- Explicit evidence, confirmation, and owner metadata for traceability.

## 2) Core Data Topology

Primary persisted artifacts:
- work-process/runtime/session.db: canonical SQLite database.
- session_events table: append-only event stream.
- optional checkpoint rows: replay acceleration.

Entity families:
- Runtime state entities: CharacterState, AdversaryState, EncounterState, QuestState.
- Rules knowledge entities: RuleChunk, RuleEntity.
- Action contracts: ActionRequest, ActionResult, StateDiff, ConfirmationRecord.

Ownership and tenancy:
- login_id is owner scope (defaulted in pre-auth mode).
- campaign_id is top-level container.
- session_id is a run inside a campaign.

## 3) Canonical Enums

SceneMode:
- exploration
- social
- combat

QuestStatus:
- new
- active
- paused
- completed
- abandoned

CampaignStatus:
- active
- archived

EventType:
- scene.changed
- test.resolved
- combat.attack_resolved
- combat.damage_applied
- combat.condition_applied
- combat.stunt_spent
- quest.updated
- progression.validated
- progression.applied
- rules.query_answered
- mutation.blocked

ActionCategory:
- state_changing
- informational

DecisionStatus:
- pending
- approved
- rejected

EntityProvenance:
- canon
- campaign
- user

## 4) Identity and Versioning

IDs:
- login_id: owner scope id (uses default in pre-auth mode).
- campaign_id: stable UUID per campaign.
- session_id: stable UUID per session.
- entity_id: stable UUID per runtime entity.
- event_id: monotonic ULID or sortable UUID.
- action_id: UUID per command.

Versioning:
- state_version increments on every committed mutation.
- events store pre_version and post_version.
- optimistic concurrency is enforced on commit.

SQLite constraints:
- event_id globally unique PRIMARY KEY.
- foreign keys enabled for each connection.

## 5) Runtime State Schemas

### 5.1 SessionState

```json
{
  "login_id": "local-dev-dm",
  "campaign_id": "uuid",
  "session_id": "uuid",
  "state_version": 12,
  "scene": {
    "mode": "combat",
    "round": 2,
    "turn_index": 3,
    "active_actor_id": "uuid"
  },
  "party": ["character_id_1", "character_id_2"],
  "adversaries": ["adversary_id_1"],
  "quests": ["quest_id_1"],
  "world_flags": {"flag_name": true},
  "updated_at": "2026-03-21T12:00:00Z"
}
```

Validation:
- scene.mode in SceneMode.
- turn_index required when mode is combat.
- referenced IDs must exist in runtime entity maps.

### 5.2 CharacterState

```json
{
  "character_id": "uuid",
  "name": "Aria",
  "level": 3,
  "class": "mage",
  "abilities": {
    "accuracy": 2,
    "communication": 1,
    "constitution": 0,
    "dexterity": 2,
    "fighting": 1,
    "intelligence": 3,
    "perception": 1,
    "strength": -1,
    "willpower": 2
  },
  "focuses": ["intelligence.arcane_lore"],
  "resources": {
    "health": {"current": 21, "max": 21},
    "fortune": {"current": 12, "max": 12},
    "mana": {"current": 18, "max": 18}
  },
  "defense": 13,
  "armor_rating": 2,
  "speed": 12,
  "talents": ["arcane_training_novice"],
  "spells": ["arcane_bolt"],
  "conditions": []
}
```

### 5.3 AdversaryState

```json
{
  "adversary_id": "uuid",
  "name": "Darkspawn Hurlock",
  "rank": "troop",
  "abilities": {"accuracy": 1, "fighting": 2, "strength": 2},
  "defense": 12,
  "armor_rating": 3,
  "speed": 10,
  "health": {"current": 25, "max": 25},
  "attacks": [
    {"name": "battle axe", "to_hit_ability": "fighting", "damage_formula": "2d6+strength"}
  ],
  "conditions": []
}
```

### 5.4 EncounterState

```json
{
  "encounter_id": "uuid",
  "participant_order": ["character_id_1", "adversary_id_1"],
  "initiative": {"character_id_1": 15, "adversary_id_1": 11},
  "round": 1,
  "turn_index": 0,
  "active_effects": []
}
```

### 5.5 QuestState

```json
{
  "quest_id": "uuid",
  "title": "The Broken Seal",
  "objective": "Find the vault entrance",
  "status": "active",
  "leads": [{"id": "lead_1", "text": "Old map fragment", "resolved": true}],
  "clues": [{"id": "clue_1", "text": "Rune sequence", "discovered": true}],
  "reveal": {"ready": false, "conditions": ["clue_1", "clue_2"]},
  "rewards": {"xp": 150, "items": ["silver_key"]}
}
```

## 6) Rules Knowledge Contracts

RuleChunk fields:
- chunk_id
- title
- chapter
- section
- text
- tags
- source_page_start/source_page_end when available

RuleEntity fields:
- entity_type
- name
- chapter
- prerequisites
- effects
- metadata
- citation_ids
- provenance (canon/campaign/user)

## 7) Action Contracts

### 7.1 ActionRequest

```json
{
  "action_id": "uuid",
  "login_id": "local-dev-dm",
  "campaign_id": "uuid",
  "session_id": "uuid",
  "category": "state_changing",
  "type": "entity.update",
  "actor_id": "dm_actor_id",
  "target_id": "character_id_1",
  "inputs": {},
  "requested_at": "2026-03-21T12:00:00Z"
}
```

### 7.2 RetrievalEvidence

```json
{
  "evidence_id": "uuid",
  "citation_id": "chunk_321",
  "source_type": "chunk",
  "score": 0.82,
  "matched_terms": ["attack", "defense"],
  "is_conflicting": false
}
```

### 7.3 ActionResult

```json
{
  "action_id": "uuid",
  "status": "resolved",
  "resolution": {},
  "formula_trace": {},
  "citations_used": ["chunk_321"],
  "warnings": []
}
```

### 7.4 StateDiff

```json
{
  "diff_id": "uuid",
  "action_id": "uuid",
  "mutations": [
    {"path": "characters.character_id_1.level", "op": "replace", "before": 2, "after": 3}
  ]
}
```

### 7.5 ConfirmationRecord

```json
{
  "confirmation_id": "uuid",
  "action_id": "uuid",
  "required": true,
  "reason": "impactful_state_change",
  "status": "approved",
  "dm_actor": "Role-DM",
  "decided_at": "2026-03-21T12:00:02Z"
}
```

## 8) Event Model

Base envelope:

```json
{
  "event_id": "ulid",
  "login_id": "local-dev-dm",
  "campaign_id": "uuid",
  "session_id": "uuid",
  "event_type": "combat.attack_resolved",
  "timestamp": "2026-03-21T12:00:02Z",
  "pre_version": 12,
  "post_version": 13,
  "action_id": "uuid",
  "payload": {},
  "citations": ["chunk_321"],
  "correlation_id": "uuid"
}
```

Important payloads:
- test.resolved: inputs, TN, result, margin.
- combat.attack_resolved: hit/miss, defense, damage, SP.
- progression.applied: selected/rejected options and stat deltas.
- mutation.blocked: reason_code, missing_evidence, required decision.

## 8.1 SQLite Physical Tables (v1)

campaigns:
- login_id TEXT NOT NULL
- campaign_id TEXT PRIMARY KEY
- name TEXT NOT NULL
- status TEXT NOT NULL
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL

sessions:
- login_id TEXT NOT NULL
- campaign_id TEXT NOT NULL
- session_id TEXT PRIMARY KEY
- state_version INTEGER NOT NULL
- scene_mode TEXT NOT NULL
- round INTEGER
- turn_index INTEGER
- active_actor_id TEXT
- payload_json TEXT NOT NULL
- updated_at TEXT NOT NULL

session_entities:
- login_id TEXT NOT NULL
- campaign_id TEXT NOT NULL
- session_id TEXT NOT NULL
- entity_type TEXT NOT NULL
- entity_id TEXT NOT NULL
- provenance TEXT NOT NULL DEFAULT 'campaign'
- is_deleted INTEGER NOT NULL DEFAULT 0
- payload_json TEXT NOT NULL
- updated_at TEXT NOT NULL
- PRIMARY KEY (session_id, entity_type, entity_id)

session_events:
- event_id TEXT PRIMARY KEY
- login_id TEXT NOT NULL
- campaign_id TEXT NOT NULL
- session_id TEXT NOT NULL
- event_type TEXT NOT NULL
- timestamp TEXT NOT NULL
- pre_version INTEGER NOT NULL
- post_version INTEGER NOT NULL
- action_id TEXT
- payload_json TEXT NOT NULL
- citations_json TEXT NOT NULL
- correlation_id TEXT

confirmations:
- confirmation_id TEXT PRIMARY KEY
- login_id TEXT NOT NULL
- campaign_id TEXT NOT NULL
- session_id TEXT NOT NULL
- action_id TEXT NOT NULL
- required INTEGER NOT NULL
- reason TEXT NOT NULL
- status TEXT NOT NULL
- dm_actor TEXT
- decided_at TEXT

command_receipts:
- login_id TEXT NOT NULL
- campaign_id TEXT NOT NULL
- session_id TEXT NOT NULL
- idempotency_key TEXT NOT NULL
- action_id TEXT NOT NULL
- action_result_json TEXT NOT NULL
- correlation_id TEXT NOT NULL
- created_at TEXT NOT NULL
- PRIMARY KEY (login_id, campaign_id, session_id, idempotency_key)

entity_mutation_warnings:
- warning_id TEXT PRIMARY KEY
- login_id TEXT NOT NULL
- campaign_id TEXT NOT NULL
- session_id TEXT NOT NULL
- entity_type TEXT NOT NULL
- entity_id TEXT NOT NULL
- provenance TEXT NOT NULL
- operation TEXT NOT NULL
- warning_message TEXT NOT NULL
- acknowledged INTEGER NOT NULL
- acknowledged_by TEXT
- acknowledged_at TEXT

runtime_config:
- config_key TEXT PRIMARY KEY
- config_value TEXT NOT NULL
- updated_at TEXT NOT NULL

schema_migrations:
- version TEXT PRIMARY KEY
- applied_at TEXT NOT NULL

Recommended indexes:
- idx_campaigns_owner on campaigns(login_id, status, updated_at)
- idx_sessions_campaign on sessions(campaign_id, updated_at)
- idx_sessions_owner_campaign on sessions(login_id, campaign_id, updated_at)
- idx_events_session_time on session_events(session_id, timestamp)
- idx_events_action on session_events(action_id)
- idx_entities_session_type on session_entities(session_id, entity_type)
- idx_confirmations_action on confirmations(action_id)
- idx_entities_provenance on session_entities(session_id, provenance, entity_type)

## 9) State Transition Rules

Allowed scene transitions:
- exploration -> social
- social -> exploration
- exploration -> combat
- social -> combat
- combat -> exploration

Guard conditions:
- combat actions require scene.mode = combat.
- progression.apply requires progression.validated in same correlation chain.
- quest completion requiring impact needs confirmation.

## 10) Retrieval Failure Policy Encoding

Policy fields:
- evidence_sufficient: boolean
- failure_policy_applied: block_state_change | warn_no_mutation
- missing_evidence_reasons: string[]
- dm_decision_required: boolean

Rules:
- state-changing + insufficient evidence -> mutation.blocked, no StateDiff commit.
- informational + insufficient evidence -> uncertain response, empty StateDiff.

## 11) Validation Rules Catalog

Cross-entity validations:
- actor/target IDs must exist for session scope.
- condition source must reference valid action/effect.
- progression choices must satisfy prerequisites.

Mutation safety validations:
- no manual decrease of state_version.
- every committed StateDiff has ActionResult + citation set.
- impactful mutation requires approved ConfirmationRecord.
- canon entity update/delete requires warning acknowledgment.
- canon delete requires warning acknowledgment plus second confirmation.
- owner scope enforcement: login_id must match campaign/session/entity owner.

## 12) Determinism and Replay

Determinism contract:
- Same ActionRequest + same evidence + same pre-state => byte-equivalent ActionResult and StateDiff.

Replay contract:
- Reapplying ordered session_events reconstructs sessions.payload_json at latest post_version.

Replay ordering:
- order by timestamp then event_id.

## 12.1 SQL DDL Reference (Condensed)

```sql
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

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
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
```

## 12.2 Integrity Rules (Application + DB)

Database-level:
- PRAGMA foreign_keys = ON per connection.
- CHECK constraints for non-negative counters where applicable.

Application-level:
- enforce post_version = pre_version + 1 on committed mutations.
- reject duplicate event_id and duplicate idempotency composite key.
- validate payload schemas before write.
- block canon update/delete when warning acknowledgment is missing.
- require delete confirmation for canon delete operations.
- block access when command login_id does not match owner scope.
- require runtime_config key default_login_id in pre-auth mode.

## 13) Minimal File Layout

- work-process/runtime/session.db
- work-process/chunks/rules_chunks_structured.jsonl
- work-process/entities/*.json

## 14) Traceability to Requirements

- Scene and lifecycle: FR-001, FR-005
- Quest and clue contracts: FR-002, FR-003
- Test and combat actions: FR-004, FR-006, FR-007, FR-008, FR-009
- Progression validation/apply: FR-010, FR-011, FR-012
- Grounded/uncertainty behavior: FR-013, FR-014, FR-016
- Confirmation and audit fields: FR-015, NFR-002, NFR-004, NFR-006
- CRUD lifecycle and safeguards: FR-017, FR-018, FR-019, FR-020, FR-021
- Multi-campaign and ownership scope: FR-022, FR-023, FR-024, FR-025

## 15) Open Data Questions

- Should owner transfer of a campaign between login_ids be supported in v1 or deferred to admin tooling?
- Should default_login_id be stored only in runtime_config or also mirrored in process env for bootstrapping?
- Should archived campaigns allow read-only session replay by default?
