# Fantasy AGE DM Assistant - Implementation Plan v1

## 1) Purpose

This plan converts approved requirements and system design into executable implementation phases with clear deliverables, acceptance criteria, and dependencies.

Inputs:
- design/handover.md
- requirements/game_requirements_v1.md
- design/system_design_v1.md
- design/data_model_v1.md
- design/engineering_principles_v1.md
- design/implementation_epic_roadmap_v1.md
- design/sprint_board_v1.md

## 2) Planning Assumptions

- SQLite is the canonical v1 persistence backend.
- Deterministic resolver is the single authority for state-changing mechanics.
- Retrieval and policy guardrails must be active before enabling mutation endpoints.

## 3) Team Roles (Lean)

- Tech Lead/Architect: API contracts, design compliance, risk ownership.
- Backend Engineer A: Orchestrator + command handlers.
- Backend Engineer B: Resolver modules + rules legality validators.
- Backend Engineer C: SQLite adapter + migrations + replay.
- QA/Automation Engineer: test harness, integration suites, performance checks.

## 4) Milestone Plan

### Milestone UX-0: UX Foundation and Interaction Specs (3-4 days, starts immediately)

Deliverables:
- Screen map and wireframes for Session Home, Exploration, Combat, Progression, Rules Assistant, and Audit.
- Interaction specs for empty/loading/error/blocked/confirmation states.
- Design tokens and initial component primitives.
- Instrumentation event map for UX telemetry.

Acceptance criteria:
- Core task flows are testable in clickable prototype or equivalent spec.
- Accessibility checks defined for keyboard, focus, and contrast.
- Every state-changing backend command has a paired UX flow definition.

Dependencies:
- requirements and system/data design baselines.

### Milestone 0: Project Scaffolding and Contracts (3-4 days)

Deliverables:
- Repo package/module layout for runtime engine.
- Typed contracts for Command, Result, Event, StateDiff, Error envelope.
- Baseline lint/type/test tooling and CI workflow.

Acceptance criteria:
- Contract validation rejects malformed payloads.
- CI runs lint + unit tests on pull request.

Dependencies:
- Final agreement on command and event envelope fields.
- UX-0 interaction specs for command and result surfaces.

### Milestone 1: SQLite Foundation (4-5 days)

Deliverables:
- Migration runner and initial SQL migrations.
- SQLite persistence adapter with transaction protocol.
- Session creation/load/update APIs.
- command_receipts idempotency support.
- runtime_config bootstrap for default_login_id and owner-scope filtering.

Acceptance criteria:
- State-changing commit path uses BEGIN IMMEDIATE and rollback semantics.
- Duplicate idempotency key returns previous result with no duplicate mutation.
- Replay of sample event stream reconstructs latest session snapshot.
- Commands fail with explicit owner-scope reason when login_id does not match resource ownership.

Dependencies:
- Contracts from Milestone 0.

### Milestone 2: Retrieval + Guardrail Layer (4-6 days)

Deliverables:
- Retrieval service integration against chunk/entity artifacts.
- Evidence scoring and sufficiency evaluator.
- DN-003 block/warn decision layer with reason codes.

Acceptance criteria:
- State-changing actions block on insufficient/conflicting evidence.
- Informational queries return uncertainty response with no mutation on weak evidence.
- Reason codes are emitted and test-verified.

Dependencies:
- Milestone 1 persistence for blocked/answered event logging.

### Milestone 3: Deterministic Exploration + Combat Core (7-9 days)

Deliverables:
- test_resolver, combat_resolver, stunt_resolver, condition_resolver.
- Handler integration for exploration.test and combat.attack.
- Confirmation gate for impactful combat outcomes.

Acceptance criteria:
- Formula traces include complete numeric components.
- Condition lifecycle and stunt legality pass integration tests.
- No direct resolver DB writes (side-effect isolation enforced).

Dependencies:
- Milestone 2 guardrails active.

### Milestone 4: Progression and Quest Flows (6-8 days)

Deliverables:
- progression.validate and progression.apply flows.
- Quest model CRUD/update and clue/reveal progression.
- Derived stat recompute and change summary output.

Acceptance criteria:
- Invalid progression choices are blocked with prerequisite reasons.
- Quest status transitions and reveal readiness rules validated.
- Impactful changes require confirmation before commit.

Dependencies:
- Milestone 3 core resolver patterns.

### Milestone 5: LLM Narration Integration (3-4 days)

Deliverables:
- LLM adapter with prompt contract and strict output envelope.
- Citation-aware response synthesis from deterministic outputs.
- Uncertainty templates for weak evidence informational answers.

Acceptance criteria:
- LLM path cannot trigger state mutation.
- Responses include citation IDs and uncertainty flag when required.
- Token/context limits enforced by configuration.

Dependencies:
- Milestone 2 retrieval and Milestone 3+ action outputs.

### Milestone 6: Hardening and Release Readiness (5-7 days)

Deliverables:
- Replay equivalence suite and deterministic repeatability tests.
- Performance benchmarks and regression thresholds.
- Backup/restore scripts and runbook validation.
- Observability dashboards/alerts and operational docs.

Acceptance criteria:
- p95 latency targets met for deterministic and DB transaction paths.
- Replay equivalence passes on seeded long sessions.
- Recovery drill meets RTO/RPO targets.

Dependencies:
- Milestones 1-5 complete.

## 5) Work Breakdown Structure (By Module)

Orchestrator:
- command validation and routing
- state machine transitions
- error envelope formatting

Resolvers:
- exploration formulas
- attack/damage/stunts
- condition stack/tick/clear
- progression prerequisite validator

Persistence:
- migrations
- transaction protocol
- receipts + replay
- checkpointing

Retrieval/Policy:
- top-k retrieval
- evidence conflict detection
- sufficiency thresholds per action category

LLM:
- prompt builder
- output parser/validator
- narrative formatter

## 6) Test Plan by Milestone

Milestone 0-1:
- contract validation tests
- migration up tests
- transaction rollback tests

Milestone 2-3:
- policy block/warn matrix tests
- resolver property tests (same input => same output)
- combat integration scenarios

Milestone 4-5:
- progression scenario tests
- quest/clue lifecycle tests
- citation/uncertainty output tests

Milestone 6:
- replay equivalence and fault injection tests
- load/performance smoke tests
- backup/restore simulation tests

## 7) Delivery Governance

Cadence:
- Weekly milestone checkpoint and risk review.
- Daily build status and blocker triage.

Artifacts per checkpoint:
- Demo scenario recordings (exploration, combat, progression).
- Test and benchmark reports.
- Updated risk register.
- UX findings summary (task success, confusion points, remediation actions).

## 8) Risk Register (Implementation)

1. Retrieval ambiguity on mechanics-critical edge cases.
- Mitigation: conservative thresholds + explicit block path + DM override event.

2. SQLite concurrency conflicts in rapid command bursts.
- Mitigation: idempotency receipts + retry policy + queueing at orchestrator boundary.

3. Adversary extraction gaps reduce combat fidelity.
- Mitigation: schema fallback for partial stat blocks + parser improvement backlog.

4. LLM response drift beyond citation evidence.
- Mitigation: strict prompt guardrails + output schema validation + fail-closed uncertainty responses.

## 9) Implementation Exit Criteria (v1)

All must be true:
- Requirements traceability matrix has no unimplemented FR/NFR entries in v1 scope.
- Release quality gates in system_design_v1 are green.
- Critical path scenarios pass end-to-end:
  - exploration test with clue update
  - combat round with stunts and condition application
  - progression validation and apply
  - informational rules query with uncertainty behavior

## 10) Immediate Next Sprint Plan (Actionable)

Sprint objective:
- Deliver Milestone UX-0 and Milestone 0, then start Milestone 1.

Sprint backlog:
1. Produce screen inventory and interaction specs for critical flows.
2. Define component tokens and accessibility acceptance checklist.
3. Create and baseline frontend acceptance matrix mapped to FR/UR IDs.
4. Create frontend component contracts mapped to command/error schemas.
5. Create prioritized UX backlog with sprint-ready stories.
6. Define and implement command/result/event typed contracts.
7. Add migration runner and create initial schema SQL.
8. Implement SQLite adapter skeleton with begin/commit/rollback.
9. Add idempotency receipt read/write path.
10. Build first integration tests for transaction safety.

Definition of sprint success:
- One end-to-end no-op command path reaches persisted event + response envelope.
- One state-changing command path proves atomic rollback under forced failure.
- One end-to-end UX flow demonstrates command -> blocked/confirmed -> resolved interaction with citations visible.

## 11) Epic Iteration Roadmap Reference

Detailed prioritized epic roadmap with frontend-testable iterations:
- work-process/design/implementation_epic_roadmap_v1.md

Detailed sprint board with points, dependencies, and e2e gates:
- work-process/design/sprint_board_v1.md
