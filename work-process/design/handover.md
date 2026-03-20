# Fantasy AGE DM Assistant - Handover

Last updated: 2026-03-21

## 1) What This Project Is

A DM-facing Fantasy AGE assistant with:
- deterministic mechanics for state-changing rules,
- retrieval-grounded rules assistance,
- SQLite persistence,
- frontend-first usability as a release concern.

## 2) Current Design Status

Design and planning are in place for:
- requirements baseline with resolved policy decisions,
- system architecture and runtime flow,
- data model and SQLite schema direction,
- frontend UX strategy and acceptance criteria,
- epic roadmap and sprint board through Sprint 8.

No full runtime implementation has been started yet (planning/design phase complete and implementation-ready).

## 3) Locked Decisions (Critical)

1. RAW-only v1 rules behavior.
2. Leveling mode selectable, default XP.
3. Retrieval failure policy:
- state-changing operations block on insufficient evidence,
- informational operations can return uncertainty with no mutation.
4. SQLite is canonical persistence backend for v1.
5. Canon entity update/delete requires warning safeguards.
6. Multi-campaign and multi-session support is required.
7. Owner scoping by login is required now using default login mode (pre-auth).

## 4) Core Artifacts to Read First

Order for next session:
1. requirements baseline:
- work-process/requirements/game_requirements_v1.md
2. architecture source of truth:
- work-process/design/system_design_v1.md
3. data contracts and schema direction:
- work-process/design/data_model_v1.md
4. frontend UX strategy and acceptance:
- work-process/design/frontend_ux_strategy_v1.md
- work-process/design/frontend_acceptance_matrix_v1.md
- work-process/design/frontend_component_contracts_v1.md
- work-process/design/frontend_backlog_v1.md
5. implementation sequencing:
- work-process/design/implementation_plan_v1.md
- work-process/design/implementation_epic_roadmap_v1.md
- work-process/design/sprint_board_v1.md
- work-process/design/sprint_board_import_v1.csv

## 5) Immediate Next Session Plan (Recommended)

Start with Sprint 1 execution from sprint_board_v1.md:
1. implement contract schemas,
2. implement SQLite migration/bootstrap,
3. implement runtime_config with default_login_id,
4. deliver command roundtrip UI path,
5. add e2e test `E2E-I1-001`.

Definition of done for next session:
- a no-op command can be sent from frontend,
- persisted event appears in DB,
- context includes login/campaign/session fields,
- validation failures are surfaced in frontend without context reset.

## 6) Guardrails That Must Not Be Broken

1. Deterministic engine remains authority for state mutations.
2. LLM output must not mutate state.
3. All mutations require auditable event persistence.
4. Owner scope (`login_id`) must gate reads and writes.
5. Canon update/delete must enforce warning + confirmation rules.
6. Every iteration must be frontend-testable end-to-end.

## 7) Known Open Questions

1. Campaign ownership transfer support in v1 or defer to admin tooling.
2. Whether default_login_id should also be mirrored via process env.
3. Archive mode behavior: read-only replay by default or restricted.

## 8) Suggested Working Conventions for Next Session

1. Treat `system_design_v1.md` and `data_model_v1.md` as contract docs.
2. If command or schema contracts change, update:
- frontend_component_contracts_v1.md,
- frontend_acceptance_matrix_v1.md,
- sprint_board_v1.md test IDs.
3. Keep story IDs and e2e IDs stable once implementation starts.

## 9) Quick Resume Checklist

1. Re-open sprint board and pick the top 2-3 Sprint 1 stories.
2. Create initial migration files and schema tests.
3. Add runtime_config seed with `default_login_id`.
4. Build minimal command endpoint + frontend submit path.
5. Add and run `E2E-I1-001`.
6. Record progress against Sprint 1 stories.

Board import file:
- work-process/design/sprint_board_import_v1.csv
