# Fantasy AGE DM Assistant - Engineering Principles and Practices v1

## 1) Purpose

This document defines baseline engineering principles and delivery practices for implementation handoff.

Goals:
- Keep deterministic mechanics correct and reproducible.
- Preserve auditability and safe state mutation.
- Maintain delivery speed without sacrificing reliability.

## 2) Core Principles

1. Deterministic First
- All state-changing mechanics are resolved by deterministic code paths.
- LLM output is advisory/narrative only and cannot mutate state.

2. Evidence-Grounded Decisions
- Mechanical outcomes require sufficient retrieval evidence.
- Insufficient/conflicting evidence follows DN-003 policy.

3. Transactional Integrity
- State mutations are atomic, version-checked, and rollback-safe.
- Never partially commit action outcomes.

4. Explainability by Default
- Every resolved action includes formula trace and citations.
- Errors are explicit and actionable.

5. Idempotent Operations
- State-changing commands require idempotency keys.
- Retried requests must return prior result without duplicate mutation.

6. Secure by Minimization
- Store only gameplay state + rule references needed for operations.
- Avoid unnecessary freeform user data retention.

7. UX as a First-Class Quality Attribute
- Usability and accessibility are release criteria, not post-implementation polish.
- A feature is not complete until user-facing states and recovery paths are implemented.

## 3) Architecture Practices

Boundaries:
- Orchestrator coordinates flow only.
- Resolver modules are pure and side-effect free.
- Persistence adapter owns SQLite transactions and schema concerns.
- LLM adapter cannot call persistence write paths.

Dependency direction:
- Domain logic does not depend on transport or UI layer.
- Resolver logic depends only on validated contracts and evidence inputs.

Contract-first development:
- Define schema for every command, result, event, and error before coding handlers.
- Reject invalid payloads at boundaries.

## 4) Code Quality Standards

Language/runtime:
- Python 3.13+ with strict typing where practical.
- Dataclasses or pydantic-style typed contracts for command/result payloads.

Style and linting:
- Ruff for linting and import hygiene.
- Black for formatting.
- Mypy (or pyright) for static type checks on core modules.

Error handling:
- Use structured error types with reason_code and remediation_hint.
- Do not swallow exceptions in resolver or persistence layers.

Logging:
- Use structured JSON logs for machine queryability.
- Include correlation_id, action_id, session_id, command_type, and outcome.

## 5) Testing Strategy and Gates

Test pyramid:
- Unit tests: resolver formulas, prerequisite checks, condition transitions.
- Integration tests: orchestrator flow with SQLite transaction boundaries.
- Policy tests: DN-003 block/warn behavior.
- Replay tests: event stream rehydration equivalence.

Mandatory pre-merge checks:
- Lint/type/tests all green.
- No new critical defects in deterministic resolution paths.
- Migration tests pass on clean DB and populated DB fixtures.

Minimum coverage targets (v1):
- Resolver modules: 90% line coverage.
- Persistence adapter: 85% line coverage.
- Orchestrator and policy logic: 80% line coverage.

## 6) SQLite Engineering Practices

Connection config:
- PRAGMA foreign_keys = ON.
- PRAGMA journal_mode = WAL.
- PRAGMA synchronous = NORMAL.
- PRAGMA busy_timeout = 5000.

Transaction rules:
- BEGIN IMMEDIATE for state-changing actions.
- Validate pre_version before any mutation write.
- Commit only after event + state + confirmation (if required) are persisted.

Migration rules:
- Forward-only SQL migration files with semantic version naming.
- Each migration runs in a single transaction.
- schema_migrations is source of truth for applied versions.

Backup/recovery drills:
- Validate restore path at least once per milestone.
- Run integrity_check in CI smoke environment where feasible.

## 7) Team Workflow Practices

Branch strategy:
- Short-lived feature branches.
- Rebase or squash-merge to keep history readable.

PR expectations:
- Small, focused PRs with one architectural concern each.
- PR template includes: requirement IDs, risks, test evidence, rollback notes.

Definition of Done:
- Contract docs updated where behavior changed.
- Tests updated and passing.
- Observability fields present for new command types.
- Failure modes documented for any new state-changing path.
- UX states (empty/loading/error/blocked/confirmation) are implemented and validated.
- Keyboard and focus behavior verified for newly added interaction paths.

## 8) Operational Readiness Practices

Observability minimum:
- Metrics: command counts, latency histograms, DB conflicts, block reasons.
- Logs: structured event on every command response.
- Alarms: latency/regression thresholds aligned with system design.

Runbooks (v1 must-have):
- Version conflict handling.
- Retrieval insufficiency handling.
- Failed migration rollback process.
- DB restore and replay process.

## 9) Documentation and Handoff Standards

Required docs for each implemented module:
- Module purpose and boundary.
- Input/output contract reference.
- Error reason codes.
- Test strategy and known limitations.

Handoff packet contents:
- Current architecture diagram and flow summary.
- Open risks and unresolved decisions.
- Implementation milestone status and next sprint scope.

## 10) Traceability

Primary requirement mappings:
- Determinism and resolver authority: NFR-001, FR-004, FR-006, FR-007.
- Traceability and explainability: NFR-002, NFR-006, FR-013.
- Reliability and rollback safety: NFR-004, FR-016, FR-015.
- Cost control and LLM boundaries: NFR-005.

## 11) Foundational Design Heuristics (DRY, SOLID, and Cohesion)

These heuristics are mandatory for new modules and refactors.

DRY (Don't Repeat Yourself):
- No duplicated business rules across orchestrator, resolver, and adapters.
- Shared validation and reason-code mapping must be centralized in contract/policy modules.
- If a rule appears in more than one place, introduce a single canonical function with tests.

SOLID guidance in this architecture:
- Single Responsibility: each module owns one reason to change (retrieval policy, resolution math, persistence, transport).
- Open/Closed: add new command/action types via registries and handler composition, not switch/if ladders in one file.
- Liskov Substitution: adapter interfaces must preserve behavior contracts (for example, persistence adapter implementations return equivalent error semantics).
- Interface Segregation: keep contracts narrow (resolver inputs should not require transport context).
- Dependency Inversion: domain logic depends on interfaces and typed contracts, not concrete Flask/SQLite details.

Cohesion and coupling targets:
- Keep side effects at boundaries; core resolver paths remain pure.
- Avoid cyclic dependencies between orchestrator, resolver, and adapter modules.
- Prefer composition over inheritance for action handlers and policy checks.

## 12) Explicit Anti-Patterns to Block

The following are release blockers until resolved:

- God module growth: one file accumulating transport, policy, persistence, and domain logic.
- Hidden state mutation: any path where LLM output directly or indirectly changes persisted state.
- Copy-paste policy logic: repeated evidence thresholds or confirmation rules in multiple handlers.
- Silent fallback behavior: swallowing errors and returning success-like responses.
- Unstructured logging in mutation paths: missing correlation and context fields for audit.
- Contract drift: endpoint payload behavior changes without schema and test updates.

## 13) Architecture Fitness Functions (CI-Enforced Direction)

Treat these as continuously checked architectural tests.

Static fitness checks:
- Contract schemas validate representative fixtures for command/result/error/event payloads.
- Lint/type checks must pass for backend and frontend projects.
- Import and layering checks should prevent domain modules importing transport-specific modules.

Dynamic fitness checks:
- Idempotency test: repeating same `idempotency_key` does not duplicate mutation.
- Transaction test: forced failure in commit path leaves state unchanged.
- Owner-scope test: reads/writes denied for mismatched `login_id`.
- Retrieval policy test: state-changing command blocks on insufficient evidence.
- Replay test: event rehydration yields deterministic state equivalence.

Evolution guardrails:
- New action type requires: contract update, resolver tests, integration tests, and observability fields.
- New persistence field requires: migration, rollback note, and backward compatibility consideration.

## 14) Stage Gates Across Delivery Pipeline

Apply these checkpoints at every implementation stage.

Design gate (before coding):
- Requirement IDs linked.
- Contract deltas listed.
- Failure modes and rollback path specified.
- SOLID/DRY impact explicitly reviewed.

Build gate (during implementation):
- Boundary checks in place (transport/orchestration/domain/persistence).
- Structured errors and reason codes implemented.
- Deterministic path covered by unit tests.

PR gate (before merge):
- Evidence of tests for happy path + failure path + idempotent retry.
- Observability fields added/updated.
- Docs and acceptance matrix updated if behavior changed.

Release gate:
- Migrations verified on clean and non-clean datasets.
- Runbook deltas captured for new failure modes.
- Frontend recovery states validated for newly introduced errors.
