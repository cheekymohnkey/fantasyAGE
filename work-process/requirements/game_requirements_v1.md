# Fantasy AGE DM Assistant - System Requirements v1

## A) Scope & Assumptions

### In scope
- A DM-facing assistant that supports rules-grounded exploration, questing, combat, and leveling workflows.
- Deterministic rules computation for state changes (health, damage, conditions, progression).
- LLM-assisted narrative output and guidance constrained by retrieved rules.
- Session state persistence for party, encounters, quests, and world flags.

### Out of scope (v1)
- Full virtual tabletop implementation.
- Automated map generation/pathfinding as core mechanic.
- Public redistribution of copyrighted full-text rulebook content.
- Fully autonomous GM behavior without DM confirmation gates.

### Assumptions
- The DM is final authority on outcomes.
- Physical dice may still be used at table; assistant accepts entered roll results.
- Rules data comes from structured entities + retrieval chunks generated in `work-process`.
- Deterministic resolver handles mechanics; LLM handles prose and options.

### Decision status
- `DN-001` (Resolved): Strict RAW mode only for v1.
- `DN-002` (Resolved): Leveling mode is selectable, defaulting to XP.
- `DN-003` (Resolved): Hybrid retrieval-failure policy.
  - State-changing mechanics (combat, progression, rewards, condition application): hard block on retrieval failure; require DM decision.
  - Non-state-changing informational queries: allow best-effort response with explicit uncertainty and no automatic state updates.
- `DN-004` (Resolved): SQLite is the v1 persistence backend for session state, events, and transactional writes.

## B) Stakeholders & Roles

- `Role-DM` (primary): Runs scenes, asks for rules guidance, confirms outcomes.
- `Role-Players` (indirect): Receive narrative and mechanical outcomes through DM.
- `Role-System` (assistant): Computes rules, tracks state, produces grounded guidance.

Success criteria
- DM can run a full session (exploration -> combat -> rewards -> progression) with consistent mechanical state.
- Assistant can cite rule sources for key rulings.

## C) Functional Requirements

### Exploration & Questing

- `FR-001` Scene State Lifecycle
  - The system must track scene type (`exploration`, `social`, `combat`) and transition events.
  - Preconditions: active session exists.
  - Postconditions: scene log entry written with timestamp and actor actions.

- `FR-002` Quest Model
  - The system must support quest objects with `objective`, `status`, `clues/leads`, `reveal`, and `rewards`.
  - Trigger: DM creates or updates a quest.
  - Alternate flow: DM can mark quest as `paused` or `abandoned`.

- `FR-003` Lead/Clue Progression
  - The system must support investigation progression using leads and clues and flag reveal readiness.
  - Trigger: successful related test or DM manual update.
  - Postconditions: clue list and reveal readiness updated.

- `FR-004` Exploration Test Resolution
  - The system must compute deterministic test outcomes from input roll + ability + focus + modifiers.
  - Postconditions: success/failure and margin recorded; optional stunt points surfaced where applicable.

### Combat

- `FR-005` Combat Encounter State
  - The system must track participants, initiative order, turn index, and per-round effects.

- `FR-006` Attack Resolution
  - The system must resolve attacks using deterministic formulas and compare to target defense.
  - Inputs: attacker, target, attack type, roll result, modifiers.
  - Outputs: hit/miss, damage, condition triggers.

- `FR-007` Damage, Health, and Defeat Handling
  - The system must apply damage to health (or Fortune if configured), track 0-health states, and present defeat options.

- `FR-008` Stunt Point Workflow
  - On eligible doubles, the system must compute SP and validate legal stunt spends for the context.
  - Alternate flow: if illegal stunt selected, system must reject with reason and legal options.

- `FR-009` Conditions Engine
  - The system must apply, stack, tick, and clear conditions according to rules metadata.

### Leveling & Progression

- `FR-010` Advancement Pipeline
  - The system must support level advancement with class-specific choices and constraints.

- `FR-011` Validation of Progression Choices
  - The system must validate prerequisites for talents, specializations, and spell/tier access.

- `FR-012` Character Sheet Recompute
  - On progression updates, the system must recompute derived stats and produce a change summary.

### Rules Assistant Behavior

- `FR-013` Grounded Rules Q&A
  - The system must answer rules questions only from retrieved chunks/entities and include citation IDs.

- `FR-014` Ambiguity Handling
  - If conflicting/insufficient evidence exists, system must return uncertainty + what is missing.

- `FR-016` Retrieval Failure Policy
  - The system must enforce hybrid failure handling:
    - Block and require DM input for state-changing mechanics when retrieval evidence is insufficient.
    - Allow best-effort informational responses with explicit uncertainty labeling and no state mutation.

- `FR-015` DM Confirmation Gates
  - For impactful state changes (death, level-up, quest completion), system must require DM confirmation.

### Entity Lifecycle and CRUD

- `FR-017` Runtime Entity CRUD
  - The system must provide create, read, update, and delete operations for all runtime game entities: `Character`, `Adversary`, `EncounterState`, and `Quest`.
  - Postconditions: each mutation writes a traceable event with actor, timestamp, and correlation id.

- `FR-018` Safe Delete and Restore Semantics
  - Delete operations for runtime entities must use soft-delete semantics by default and support explicit restore.
  - Hard delete is disallowed in normal DM workflows and reserved for maintenance utilities.

- `FR-019` Filtered Read and List Operations
  - The system must support filtered list/read operations by `entity_type`, `status`, `scene relevance`, and `updated_at` ranges.
  - Read/list operations must preserve access to audit metadata and latest revision identifiers.

- `FR-020` Canon Entity Mutation Warning
  - Before any update or delete operation on canon entities, the system must show a high-visibility warning describing impact and require explicit DM acknowledgment.
  - Canon entities are rules-sourced entities with canon provenance (for example rules chunks/entities derived from source material).

- `FR-021` Canon Delete Safeguard
  - Deleting canon entities must require a second-step confirmation after warning acknowledgment.
  - If acknowledgment or confirmation is absent, mutation must be blocked with a clear reason code and no state change.

- `FR-022` Multi-Campaign and Multi-Session Support
  - The system must support multiple campaigns, each containing one or more play sessions/runs.
  - The DM must be able to create, list, open, and archive campaigns, and create/list/open sessions within a selected campaign.

- `FR-023` Campaign Isolation Guarantees
  - Runtime state, event logs, and entity mutations must be isolated per campaign and per session.
  - Cross-campaign reads or mutations are disallowed unless explicitly requested through administrative export/import tooling.

- `FR-024` Login-Scoped Ownership
  - Campaigns, sessions, characters, adversaries, quests, and related runtime entities must be scoped to a `login_id` owner context.
  - All read/list/mutation operations must be filtered by active `login_id` and rejected when owner scope does not match.

- `FR-025` Default Login Mode (Pre-Authentication)
  - Until authentication is implemented, the system must run with a configurable default `login_id` and use it as mandatory owner context.
  - The default `login_id` must be centrally configurable and auditable in runtime metadata.

## D) Non-Functional Requirements

- `NFR-001` Determinism
  - Identical mechanical inputs must produce identical outputs.

- `NFR-002` Traceability
  - Every resolved action must store source inputs, output, and rule references.

- `NFR-003` Latency
  - Deterministic resolution target: <= 150 ms local execution per action (excluding LLM latency).

- `NFR-004` Reliability
  - No silent state corruption; failed writes must be retried or transactionally rolled back.

- `NFR-005` LLM Cost Control
  - Prefer deterministic resolver first; only call LLM for narrative/guidance and capped context windows.

- `NFR-006` Explainability
  - Each computed result must be human-readable in DM terms (inputs, formula, output).

## E) Domain Model & Data Requirements

Core entities
- `Character`: attributes, focuses, class, talents, spells, resources, conditions.
- `Adversary`: stat block, attacks, threat, special rules.
- `EncounterState`: scene mode, initiative, turn state, effects, event log.
- `Quest`: objectives, leads, clues, reveal, rewards, status.
- `RuleChunk`: retrieval text unit with metadata and citation id.
- `RuleEntity`: structured rule object (spell, stunt, talent, etc.).

Validation rules
- Combat actions require active combat scene.
- Level-up requires rule-valid prerequisites.
- Condition application requires valid source effect.

## F) Use Case Catalog (Priority)

1. Run exploration test with clue discovery.
2. Run combat round with attack, damage, condition, and stunts.
3. Ask rules question and receive citation-backed answer.
4. Apply rewards and perform level progression validation.

## G) Acceptance Criteria (Gherkin)

```gherkin
Scenario: Resolve exploration ability test
  Given an active exploration scene and a character with ability and focus values
  When the DM enters a roll result and modifiers
  Then the system computes deterministic success/failure
  And stores a scene log entry with formula inputs and output
```

```gherkin
Scenario: Compute stunt options in combat
  Given an active combat scene and a successful eligible roll with doubles
  When stunt points are generated
  Then the system shows only legal stunts for that context
  And rejects illegal spends with a clear reason
```

```gherkin
Scenario: Validate level-up prerequisites
  Given a character leveling up
  When the DM selects talents and specialization options
  Then invalid options are blocked with prerequisite explanations
  And valid changes recalculate derived stats
```

## H) Traceability Matrix (Condensed)

- Core resolution -> `FR-004`, `FR-006`, `NFR-001`
- Stunts/conditions -> `FR-008`, `FR-009`
- Questing/investigation -> `FR-002`, `FR-003`
- Advancement -> `FR-010`, `FR-011`, `FR-012`
- Grounded assistant -> `FR-013`, `FR-014`, `NFR-002`
- Entity lifecycle CRUD -> `FR-017`, `FR-018`, `FR-019`, `NFR-002`, `NFR-004`
- Canon mutation guardrails -> `FR-020`, `FR-021`, `FR-015`, `NFR-004`, `NFR-006`
- Multi-campaign lifecycle and isolation -> `FR-022`, `FR-023`, `NFR-002`, `NFR-004`
- Login ownership scoping -> `FR-024`, `FR-025`, `NFR-002`, `NFR-004`

## I) Risks & Dependencies

Risks
- OCR/PDF artifacts can still create edge-case parsing errors.
- Ambiguous rule interactions may require DM override pathways.
- Over-reliance on LLM can degrade determinism.

Dependencies
- Canonical pipeline outputs must be current and strict-pass.
- Adversary stat parsing must be completed for combat automation quality.

Mitigations
- Keep strict validator as release gate.
- Add DM override + audit log for every override.
- Use deterministic engine as first-class authority.

## J) MVP Cutline

### Phase 1 (MVP)
- Exploration test resolution + clue/quest tracking.
- Combat core loop (attack/damage/health/conditions/stunts).
- Rules Q&A with citations and uncertainty behavior.

### Phase 2
- Full progression assistant (talent/specialization/spell choice guards).
- Encounter recommendation helpers from adversary dataset.

### Future
- Advanced campaign analytics, encounter simulation, optional VTT connectors.

## Immediate Next Requirement Decisions

- Confirm whether to enforce hard blocking on unresolved ambiguity in combat-critical rulings.
