# Fantasy AGE DM Assistant - Epic Implementation Roadmap v1

## 1) Purpose

This roadmap defines a prioritized, iterative implementation sequence by epic, where each iteration is end-to-end testable through the frontend.

Planning constraints:
- Every iteration ships a thin vertical slice: UI flow -> API/command handler -> domain logic -> SQLite persistence -> observable result.
- No backend-only milestone is considered complete without a frontend path and e2e test evidence.
- Owner scope (`login_id`), campaign/session context, and canon safeguards are enforced from early iterations.

## 2) Prioritization Logic

Priority order factors:
1. Foundational risk reduction (contracts, persistence, owner scope).
2. Live-session value (exploration/combat first).
3. Safety controls (confirmation, canon warning, mutation guardrails).
4. Feature expansion (progression, questing, assistant quality).
5. Hardening and release operations.

## 3) Epic Stack (Ordered)

1. EP-01 Platform Foundation and Contracts
2. EP-02 Ownership, Campaign, and Session Management
3. EP-03 Entity CRUD and Canon Safety
4. EP-04 Exploration Vertical Slice
5. EP-05 Combat Vertical Slice
6. EP-06 Progression and Quest Vertical Slice
7. EP-07 Rules Assistant and Evidence UX
8. EP-08 Reliability, Replay, and Operability

## 4) Iteration Plan (Frontend-Testable Slices)

### Iteration 1: Foundation Slice (EP-01)

Goal:
- Establish command/event contracts, default login context, and a minimal command roundtrip visible in UI.

Backend scope:
- Contract schemas for command/result/error/event envelopes.
- Runtime config loader with `default_login_id`.
- SQLite bootstrap and migration runner.

Frontend scope:
- Login Context Banner (pre-auth default mode).
- Command Bar submits a no-op diagnostic command.
- Standard error surface for validation failures.

E2E scenario:
- From UI, submit diagnostic command and view persisted event summary.
- Invalid payload surfaces mapped validation error without losing input.

Exit criteria:
- E2E test `I1_CommandRoundtrip_DefaultLogin` passes.
- Audit row exists with `login_id`, `campaign_id`, `session_id` when context is present.

### Iteration 2: Campaign/Session Slice (EP-02)

Goal:
- Create/list/open/archive campaigns and create/list/open sessions from UI with strict context validation.

Backend scope:
- `campaign.create/list/open/archive` commands.
- `session.create/list/open` commands.
- `precondition.campaign_session_mismatch` and `precondition.owner_scope_mismatch` enforcement.

Frontend scope:
- Campaign and Session Selector UI.
- Context mismatch recovery banner.
- Session Home context strip with active campaign/session.

E2E scenario:
- Create campaign -> create session -> open session -> submit command in valid context.
- Attempt command with mismatched session and confirm block behavior.

Exit criteria:
- E2E tests `I2_CreateAndOpenSession` and `I2_BlockMismatchedContext` pass.
- Owner scope filter confirmed in list endpoints.

### Iteration 3: CRUD + Canon Safety Slice (EP-03)

Goal:
- Deliver CRUD for runtime entities with canon update/delete warning guardrails.

Backend scope:
- `entity.create/read/list/update/delete` commands for Character, Adversary, EncounterState, Quest.
- Soft-delete default behavior.
- Canon warning acknowledgment and delete double-confirmation enforcement.

Frontend scope:
- Entity Management flows.
- CanonMutationWarningModal and confirmation tray chaining.
- Filter/list controls (`status`, `updated_at`, `entity_type`).

E2E scenario:
- Create character, update character, soft-delete and restore.
- Attempt canon update/delete and verify warning and double-confirm flow.

Exit criteria:
- E2E tests `I3_EntityCrudHappyPath` and `I3_CanonDeleteGuard` pass.
- No mutation occurs without required warnings/confirmations.

### Iteration 4: Exploration Slice (EP-04)

Goal:
- Resolve exploration tests with clue progression and explainable outputs.

Backend scope:
- `exploration.test` command handler and deterministic resolver.
- Clue/lead update linkage.
- Formula trace + citation packaging.

Frontend scope:
- Exploration test widget.
- Clue/lead board updates in place.
- Result card with formula + citation drill-down.

E2E scenario:
- Run exploration test from UI and verify deterministic outcome plus clue update.

Exit criteria:
- E2E test `I4_ExplorationTestWithClueUpdate` passes.
- Median interaction time meets UR target threshold in test run.

### Iteration 5: Combat Slice (EP-05)

Goal:
- Execute one full combat turn including attack, stunts, conditions, and confirmations.

Backend scope:
- `combat.attack`, stunt legality checks, condition lifecycle operations.
- Confirmation gate for impactful outcomes.

Frontend scope:
- Combat Console with initiative ladder and active turn card.
- Stunt selector with legal option feedback.
- Condition chips/timers and mutation summaries.

E2E scenario:
- Resolve attack -> spend legal stunt -> apply condition -> confirm impactful mutation.
- Attempt illegal stunt and verify safe recovery.

Exit criteria:
- E2E tests `I5_CombatTurnHappyPath` and `I5_IllegalStuntRecovery` pass.
- No direct UI flow allows mutation bypassing confirmation gate.

### Iteration 6: Progression + Quest Slice (EP-06)

Goal:
- Ship progression validate/apply and quest lifecycle updates with guarded mutations.

Backend scope:
- `progression.validate`, `progression.apply`.
- Quest CRUD/status transitions and reveal readiness rules.

Frontend scope:
- Progression Workspace with prerequisite feedback.
- Diff preview + confirmation for apply.
- Quest tracker lifecycle controls.

E2E scenario:
- Run progression validate -> apply -> verify stat recompute.
- Update quest to completed with required confirmation path.

Exit criteria:
- E2E tests `I6_ProgressionApplyGuarded` and `I6_QuestLifecycleGuarded` pass.

### Iteration 7: Rules Assistant Slice (EP-07)

Goal:
- Grounded Q&A with uncertainty handling and no-mutation guarantees for weak evidence.

Backend scope:
- `rules.query` pipeline with retrieval sufficiency thresholds.
- Block/warn reason codes and uncertainty envelope.

Frontend scope:
- Rules Assistant response cards with citations.
- Uncertainty banner and evidence drawer.

E2E scenario:
- Strong-evidence query returns grounded answer.
- Weak-evidence query returns uncertainty and no state mutation.

Exit criteria:
- E2E tests `I7_GroundedQuery` and `I7_WeakEvidenceNoMutation` pass.

### Iteration 8: Hardening Slice (EP-08)

Goal:
- Achieve release-grade reliability, replay integrity, and operational readiness.

Backend scope:
- Replay equivalence suite, backup/restore utilities, fault-injection cases.
- Performance and conflict telemetry.

Frontend scope:
- Audit and replay view.
- Operational state indicators for blocked actions, retries, and integrity alerts.

E2E scenario:
- Run seeded session, replay to latest state, verify equivalence.
- Simulate persistence conflict and confirm user recovery path.

Exit criteria:
- E2E tests `I8_ReplayEquivalence` and `I8_ConflictRecoveryUX` pass.
- Release gates from system design all green.

## 5) Epic-to-Iteration Mapping

- EP-01: Iteration 1
- EP-02: Iteration 2
- EP-03: Iteration 3
- EP-04: Iteration 4
- EP-05: Iteration 5
- EP-06: Iteration 6
- EP-07: Iteration 7
- EP-08: Iteration 8

## 6) Definition of Iteration Done

An iteration is complete only if all are true:
1. Frontend flow is usable for the targeted slice.
2. Backend command path persists auditable events.
3. Required guardrails are enforced (`login_id`, campaign/session scope, canon safety, confirmations as applicable).
4. At least one named e2e scenario passes in CI.
5. Telemetry events for success and blocked outcomes are emitted.
6. Regression suite for previously completed iterations remains green.

## 7) CI/CD Gate Model

Per pull request:
- Contract tests.
- Unit tests for touched modules.
- Frontend component tests for affected flows.

Per iteration merge gate:
- End-to-end test suite for current and prior iterations.
- Accessibility checks for changed screens.
- Migration up test on clean and fixture DB.

Per release candidate:
- Replay equivalence, performance baseline, backup/restore drills.

## 8) Suggested Timeline (Lean Team)

- Iteration 1: 1 week
- Iteration 2: 1 week
- Iteration 3: 1 to 1.5 weeks
- Iteration 4: 1 week
- Iteration 5: 1.5 weeks
- Iteration 6: 1 to 1.5 weeks
- Iteration 7: 1 week
- Iteration 8: 1 week

Total estimate: 9 to 10.5 weeks, depending on combat and progression complexity.

## 9) Immediate Next Actions

1. Create e2e test skeletons using iteration test IDs in this roadmap.
2. Add EP- and iteration labels in project tracking for visibility.
3. Freeze command/result/error contract versions for Iteration 1 and 2 scope.

Execution board reference:
- work-process/design/sprint_board_v1.md

Sprint-to-iteration alignment reference:
- Sprint 5 maps to Iteration 5 (Combat Vertical Slice).
- Sprint 6 maps to Iteration 6 (Progression + Quest Vertical Slice).
- Sprint 7 maps to Iteration 7 (Rules Assistant Vertical Slice).
- Sprint 8 maps to Iteration 8 (Hardening and Release Readiness).
