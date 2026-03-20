# Fantasy AGE DM Assistant - Architecture Governance Checklist v1

Purpose:
Use this checklist during design review, implementation, and pull request review. It operationalizes DRY/SOLID and system guardrails so architecture quality is continuously enforced.

## 1) Design Review Checklist

- [ ] Requirement IDs are linked for every behavioral change.
- [ ] Command/result/error/event schema deltas are identified and reviewed.
- [ ] Boundary ownership is clear:
  - [ ] transport layer
  - [ ] orchestration layer
  - [ ] deterministic resolver layer
  - [ ] persistence adapter layer
- [ ] SOLID review completed:
  - [ ] SRP: single reason to change per module
  - [ ] OCP: extension via composition/registration, not branching sprawl
  - [ ] ISP/DIP: domain contracts do not depend on Flask/SQLite details
- [ ] DRY review completed:
  - [ ] no duplicate policy thresholds
  - [ ] no duplicate reason-code mapping
  - [ ] no duplicated validation logic
- [ ] Failure modes are explicitly listed with reason codes and recovery behavior.
- [ ] Rollback strategy exists for schema or behavior changes.

## 2) Implementation Checklist

- [ ] Input contracts validated at boundary before business logic execution.
- [ ] State mutation path is deterministic and isolated from LLM output.
- [ ] State-changing actions enforce idempotency key semantics.
- [ ] Persistence writes are atomic and rollback-safe.
- [ ] Owner scope (`login_id`) gates all read/write paths.
- [ ] Guardrail policy for insufficient/conflicting evidence is implemented.
- [ ] Logs include correlation_id, action_id, session_id, command_type, outcome.
- [ ] Tests cover:
  - [ ] happy path
  - [ ] validation/precondition failure
  - [ ] idempotent retry
  - [ ] transaction rollback path

## 3) PR Review Checklist

- [ ] Architectural impact summary included in PR description.
- [ ] Behavioral changes mapped to updated docs/contracts.
- [ ] New/changed migrations include test evidence.
- [ ] Observability updates included for new mutation paths.
- [ ] Frontend error/blocked/confirmation states verified when relevant.
- [ ] Added complexity is justified; simpler alternatives considered.

## 4) Release Readiness Checklist

- [ ] Migrations validated on fresh and existing DB states.
- [ ] Replay and auditability behavior verified for new event types.
- [ ] Runbook updates captured for newly introduced failure modes.
- [ ] CI gates are green for backend and frontend checks.

## 5) Trigger Conditions (Mandatory Review)

Run full checklist when any of the following changes occur:

- New command/action type.
- Any change to state mutation pipeline.
- Any schema/migration update.
- Any owner-scope/authorization behavior change.
- Any change to retrieval sufficiency policy.
