# Fantasy AGE DM Assistant - Sprint Board v1

## 1) Purpose

Execution board for the first four implementation sprints, aligned to the epic roadmap and designed for iterative end-to-end frontend-testable delivery.

Planning assumptions:
- Team capacity baseline: 28-34 points per sprint.
- Points scale: 1 (tiny), 2 (small), 3 (medium), 5 (large), 8 (very large).
- Each sprint includes at least one mandatory e2e scenario.

Tracker import companion:
- work-process/design/sprint_board_import_v1.csv

## 2) Sprint 1 (Foundation and Context)

Sprint objective:
- Ship the first vertical slice: UI command roundtrip with default login context and auditable persistence.

Target epics:
- EP-01 Platform Foundation and Contracts
- EP-02 Ownership, Campaign, and Session Management (initial slice)

Stories:
1. SB-1-01 Define command/result/error/event schemas (5)
- Dependencies: none
- Deliverables: versioned schema definitions and contract fixtures
- Test IDs: CT-001, CT-002

2. SB-1-02 SQLite migration runner and base schema bootstrap (8)
- Dependencies: SB-1-01
- Deliverables: migration runner, initial migrations
- Test IDs: DB-001, DB-002

3. SB-1-03 Runtime config bootstrap with default_login_id (3)
- Dependencies: SB-1-02
- Deliverables: runtime_config loader and default key check
- Test IDs: CFG-001

4. SB-1-04 Frontend Login Context Banner + global command bar no-op submit (5)
- Dependencies: SB-1-01, SB-1-03
- Deliverables: context banner and submit flow
- Test IDs: FE-001, FE-002

5. SB-1-05 Persist no-op command event and display summary in Session Home (5)
- Dependencies: SB-1-02, SB-1-04
- Deliverables: end-to-end diagnostic command path
- Test IDs: E2E-I1-001

6. SB-1-06 Validation error mapping and recovery UX (3)
- Dependencies: SB-1-01, SB-1-04
- Deliverables: standardized validation surface
- Test IDs: FE-ERR-001

Sprint total: 29 points

Mandatory e2e gate:
- E2E-I1-001 Command roundtrip with default login context.

## 3) Sprint 2 (Campaign and Session Context)

Sprint objective:
- Deliver campaign/session lifecycle from UI with strict owner and context isolation.

Target epics:
- EP-02 Ownership, Campaign, and Session Management

Stories:
1. SB-2-01 Implement campaign.create/list/open/archive commands (8)
- Dependencies: Sprint 1 complete
- Test IDs: API-CAMP-001

2. SB-2-02 Implement session.create/list/open commands (5)
- Dependencies: SB-2-01
- Test IDs: API-SESS-001

3. SB-2-03 Owner scope mismatch and campaign/session mismatch guards (5)
- Dependencies: SB-2-01, SB-2-02
- Test IDs: POL-CTX-001, POL-OWN-001

4. SB-2-04 Frontend Campaign and Session Selector with context banner recovery (5)
- Dependencies: SB-2-01, SB-2-02
- Test IDs: FE-CONTEXT-001

5. SB-2-05 Context-scoped list filtering and session home refresh behaviors (3)
- Dependencies: SB-2-03, SB-2-04
- Test IDs: FE-CONTEXT-002

6. SB-2-06 Telemetry for context switch and mismatch block events (2)
- Dependencies: SB-2-04
- Test IDs: TELE-CTX-001

Sprint total: 28 points

Mandatory e2e gates:
- E2E-I2-001 Create campaign -> create session -> open -> command success.
- E2E-I2-002 Mismatched campaign/session blocked with guided recovery.

## 4) Sprint 3 (Entity CRUD and Canon Safety)

Sprint objective:
- Ship full runtime entity CRUD with canon warning and delete double-confirm safeguards.

Target epics:
- EP-03 Entity CRUD and Canon Safety

Stories:
1. SB-3-01 Implement entity.create/read/list/update/delete command handlers (8)
- Dependencies: Sprint 2 complete
- Test IDs: API-CRUD-001

2. SB-3-02 Soft-delete and restore semantics for runtime entities (5)
- Dependencies: SB-3-01
- Test IDs: API-CRUD-002

3. SB-3-03 Canon warning acknowledgment and delete double-confirm backend enforcement (5)
- Dependencies: SB-3-01
- Test IDs: POL-CANON-001, POL-CANON-002

4. SB-3-04 Frontend Entity Management console (CRUD + filter controls) (5)
- Dependencies: SB-3-01, SB-3-02
- Test IDs: FE-CRUD-001

5. SB-3-05 CanonMutationWarningModal + confirmation chaining UX (5)
- Dependencies: SB-3-03, SB-3-04
- Test IDs: FE-CANON-001

6. SB-3-06 Audit event and telemetry coverage for CRUD/canon actions (3)
- Dependencies: SB-3-03, SB-3-05
- Test IDs: TELE-CRUD-001

Sprint total: 31 points

Mandatory e2e gates:
- E2E-I3-001 Runtime entity CRUD happy path.
- E2E-I3-002 Canon delete blocked until warning acknowledgment and second confirmation.

## 5) Sprint 4 (Exploration Vertical Slice)

Sprint objective:
- Deliver exploration test resolution with clue progression and explainable, cited output.

Target epics:
- EP-04 Exploration Vertical Slice

Stories:
1. SB-4-01 Implement exploration.test deterministic resolver and handler (8)
- Dependencies: Sprint 3 complete
- Test IDs: RES-EXP-001

2. SB-4-02 Connect clue/lead updates to exploration outcomes (5)
- Dependencies: SB-4-01
- Test IDs: RES-EXP-002

3. SB-4-03 Retrieval evidence packaging and formula trace output for exploration flow (5)
- Dependencies: SB-4-01
- Test IDs: RET-EXP-001

4. SB-4-04 Frontend Exploration test widget with result card integration (5)
- Dependencies: SB-4-01, SB-4-03
- Test IDs: FE-EXP-001

5. SB-4-05 Clue board inline updates and citation drill-down drawer behavior (3)
- Dependencies: SB-4-02, SB-4-04
- Test IDs: FE-EXP-002

6. SB-4-06 UX timing benchmark and telemetry verification for exploration path (2)
- Dependencies: SB-4-04
- Test IDs: PERF-EXP-001, TELE-EXP-001

Sprint total: 28 points

Mandatory e2e gate:
- E2E-I4-001 Exploration test updates clue state with formula and citation visibility.

## 6) Cross-Sprint Exit Gates

Every sprint must pass:
1. All mandatory e2e gates for that sprint.
2. Regression e2e gates from prior sprints.
3. Contract compatibility checks with existing frontend fixtures.
4. Accessibility checks for newly introduced flows.
5. Telemetry event assertions for success and blocked paths.

## 7) Board Operations

Recommended board columns:
- Backlog
- Ready
- In Progress
- In Review
- QA/E2E
- Done

Recommended labels:
- epic:EP-01..EP-08
- sprint:S1..S4
- area:frontend | backend | persistence | retrieval | qa
- risk:high | medium | low

## 8) Next Board Extension

After Sprint 4 completion, generate Sprint 5-8 board slices from the same template:
- Sprint 5: Combat vertical slice
- Sprint 6: Progression + Quest vertical slice
- Sprint 7: Rules Assistant vertical slice
- Sprint 8: Hardening and release readiness

## 9) Sprint 5 (Combat Vertical Slice)

Sprint objective:
- Deliver one full combat turn through UI with deterministic resolution, stunt legality, condition handling, and confirmation gates.

Target epics:
- EP-05 Combat Vertical Slice

Stories:
1. SB-5-01 Implement combat.attack handler + deterministic to-hit/damage output (8)
- Dependencies: Sprint 4 complete
- Test IDs: API-CMB-001, RES-CMB-001

2. SB-5-02 Implement stunt legality and illegal-stunt reason paths (5)
- Dependencies: SB-5-01
- Test IDs: RES-CMB-002, POL-CMB-001

3. SB-5-03 Implement condition apply/tick/clear command support (5)
- Dependencies: SB-5-01
- Test IDs: API-CMB-002, RES-CND-001

4. SB-5-04 Frontend Combat Console with initiative ladder + active turn card (5)
- Dependencies: SB-5-01
- Test IDs: FE-CMB-001

5. SB-5-05 Frontend stunt selector, illegal recovery, and condition chips/timers (5)
- Dependencies: SB-5-02, SB-5-03, SB-5-04
- Test IDs: FE-CMB-002

6. SB-5-06 Impactful combat confirmation tray + telemetry assertions (3)
- Dependencies: SB-5-01, SB-5-04
- Test IDs: FE-CMB-003, TELE-CMB-001

Sprint total: 31 points

Mandatory e2e gates:
- E2E-I5-001 Combat turn happy path (attack -> legal stunt -> condition apply -> confirmation).
- E2E-I5-002 Illegal stunt recovery without state corruption.

## 10) Sprint 6 (Progression and Quest Vertical Slice)

Sprint objective:
- Deliver guarded progression and quest lifecycle operations with UI diff preview and confirmation-driven apply.

Target epics:
- EP-06 Progression and Quest Vertical Slice

Stories:
1. SB-6-01 Implement progression.validate with prerequisite diagnostics (5)
- Dependencies: Sprint 5 complete
- Test IDs: API-PRG-001, RES-PRG-001

2. SB-6-02 Implement progression.apply + derived stat recompute (8)
- Dependencies: SB-6-01
- Test IDs: API-PRG-002, RES-PRG-002

3. SB-6-03 Implement quest status transitions + reveal readiness rules (5)
- Dependencies: Sprint 5 complete
- Test IDs: API-QST-001, RES-QST-001

4. SB-6-04 Frontend Progression Workspace validation + diff preview (5)
- Dependencies: SB-6-01, SB-6-02
- Test IDs: FE-PRG-001

5. SB-6-05 Frontend Quest tracker lifecycle controls with guard messages (5)
- Dependencies: SB-6-03
- Test IDs: FE-QST-001

6. SB-6-06 Confirmation gating + telemetry for progression/quest impactful updates (3)
- Dependencies: SB-6-02, SB-6-05
- Test IDs: FE-PRG-002, TELE-QST-001

Sprint total: 31 points

Mandatory e2e gates:
- E2E-I6-001 Progression validate/apply guarded flow.
- E2E-I6-002 Quest lifecycle update with confirmation on impactful transition.

## 11) Sprint 7 (Rules Assistant Vertical Slice)

Sprint objective:
- Deliver grounded rules Q&A with evidence visibility and strict uncertainty/no-mutation behavior.

Target epics:
- EP-07 Rules Assistant and Evidence UX

Stories:
1. SB-7-01 Implement rules.query retrieval pipeline with sufficiency thresholds (8)
- Dependencies: Sprint 6 complete
- Test IDs: API-RUL-001, RET-001

2. SB-7-02 Implement uncertainty and block/warn response envelopes (5)
- Dependencies: SB-7-01
- Test IDs: POL-RUL-001

3. SB-7-03 Implement citation packaging and evidence conflict metadata (5)
- Dependencies: SB-7-01
- Test IDs: RET-002

4. SB-7-04 Frontend Rules Assistant cards + citation chips + evidence drawer (5)
- Dependencies: SB-7-01, SB-7-03
- Test IDs: FE-RUL-001

5. SB-7-05 Frontend uncertainty banner and explicit no-mutation messaging (3)
- Dependencies: SB-7-02, SB-7-04
- Test IDs: FE-RUL-002

6. SB-7-06 Telemetry and UX analytics hooks for query outcomes (2)
- Dependencies: SB-7-04
- Test IDs: TELE-RUL-001

Sprint total: 28 points

Mandatory e2e gates:
- E2E-I7-001 Strong-evidence grounded query with citations.
- E2E-I7-002 Weak-evidence query returns uncertainty and no state mutation.

## 12) Sprint 8 (Hardening and Release Readiness)

Sprint objective:
- Reach release-grade reliability with replay guarantees, operational tooling, and frontend recovery pathways.

Target epics:
- EP-08 Reliability, Replay, and Operability

Stories:
1. SB-8-01 Replay equivalence suite for seeded campaign/session runs (8)
- Dependencies: Sprint 7 complete
- Test IDs: REL-RPL-001, REL-RPL-002

2. SB-8-02 Backup/restore and integrity check automation (5)
- Dependencies: Sprint 7 complete
- Test IDs: OPS-BKP-001, OPS-BKP-002

3. SB-8-03 Fault-injection coverage for persistence conflicts and retries (5)
- Dependencies: SB-8-01
- Test IDs: REL-FTI-001

4. SB-8-04 Frontend Audit and Replay view with correlation drill-down (5)
- Dependencies: SB-8-01
- Test IDs: FE-AUD-001

5. SB-8-05 Frontend conflict recovery UX and retry guidance (3)
- Dependencies: SB-8-03, SB-8-04
- Test IDs: FE-AUD-002

6. SB-8-06 Performance and accessibility final regression gate (3)
- Dependencies: SB-8-04, SB-8-05
- Test IDs: PERF-RC-001, A11Y-RC-001

Sprint total: 29 points

Mandatory e2e gates:
- E2E-I8-001 Replay equivalence from event stream to latest session snapshot.
- E2E-I8-002 Persistence conflict recovery from UI with safe retry path.

## 13) Full Program Gate

Program release readiness requires:
1. All mandatory e2e gates E2E-I1-001 through E2E-I8-002 are passing.
2. No unresolved P0 stories in sprints 1-8.
3. Regression suite and accessibility checks remain green on release candidate branch.
