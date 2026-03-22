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
5. engineering and architecture quality gates:
- work-process/design/engineering_principles_v1.md
- work-process/design/architecture_governance_checklist_v1.md
6. implementation sequencing:
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
4. For every design/implementation/PR cycle, run the architecture governance checklist (`work-process/design/architecture_governance_checklist_v1.md`) and capture any failed checks as explicit follow-up tasks.

## 9) Quick Resume Checklist

1. Re-open sprint board and pick the top 2-3 Sprint 1 stories.
2. Create initial migration files and schema tests.
3. Add runtime_config seed with `default_login_id`.
4. Build minimal command endpoint + frontend submit path.
5. Add and run `E2E-I1-001`.
6. Record progress against Sprint 1 stories.


## Selected Next Task

Current selection for the next session work (picked by the team):

- **SB-2-01 — Implement campaign.create/list/open/archive commands**: Completed
	- Reason: required Sprint 2 story to enable multi-campaign and owner-scoped session context flows.
	- Owner: backend team
	- Target: add Campaign command handlers and API end-to-end coverage for command and session context.

- **SB-2-02 — Implement session.create/list/open commands**: Completed
	- Reason: required to enable campaign-scoped session lifecycle and strict context validation.
	- Owner: backend team
	- Target: add Session command handlers and API end-to-end coverage for context switch and guard rails.

- **SB-2-03 — Owner scope and campaign/session mismatch guards**: Completed
	- Reason: enforcement layer after session lifecycle commands, per EP-02 security expectations.
	- Owner: backend team
	- Target: ensure precondition errors and ownership blockers on cross-scope data.

- **SB-2-04 — Frontend Campaign and Session Selector with context banner recovery**: Completed
	- Reason: required to complete ui/ux flow for campaign/session-scoped context and recovery instructions.
	- Owner: frontend team
	- Target: add context mismatch banner, reset path, and session selector behavior.

- **SB-2-06 — Telemetry for context switch and mismatch block events**: Completed
	- Reason: this closes telemetry verification in EP-02 and prepares analytics hooks.
	- Owner: backend+frontend team
	- Target: emit telemetry event on context switch, precondition mismatch, and owner scope blocks.

- **SB-3-01 — Implement entity.create/read/list/update/delete with soft delete canon safety**: In progress
	- Reason: next EP-03 core entity CRUD vertical slice.
	- Owner: backend team
	- Target: session-scoped entity management with owner scope guards and audit compliance.


## 12) Shared Utilities

We maintain a short registry of shared utility functions to improve discoverability and encourage a stable public surface for helpers used across the codebase.

- Registry doc: `work-process/design/shared_utils.md`
- Current canonical helpers:
	- `backend.timeutils.utc_now_z()` — timezone-aware UTC ISO8601 timestamps (also re-exported at `backend.utc_now_z`).

Guidance:
- Add entries to `work-process/design/shared_utils.md` when a utility is reused across multiple modules.
- Re-export public helpers from `backend/__init__.py` to make imports simpler for callers and tests.

Best practices
- Prefer abstracting reusable components into shared utilities instead of copying similar code across modules. This reduces duplication, centralizes behavior, and makes testing easier.
- Document the helper's intended audience and stability in `work-process/design/shared_utils.md` when adding to the registry.
- Keep helpers small and focused; avoid adding broad, domain-specific logic into `backend/` utilities — those belong to feature modules.


## 10) Current Implementation Status

Progress updates (working notes):

- **SB-1-01 (Define command/result/error/event schemas):** Completed — initial JSON Schema and example fixtures added on 2026-03-21. See `work-process/schemas/command_event.schema.json` and `work-process/design/contract_fixtures/command_event_example.json`.
- **SB-1-02 (SQLite migration runner and base schema bootstrap):** Next up and in-progress (developer started schema/fixture work). Target: create migration runner and initial migrations, and add schema migration tests.

- **SB-1-02 (SQLite migration runner and base schema bootstrap):** Completed — migration runner added (`work-process/scripts/migrate.py`) and initial migrations applied. Schema migration tests added (`tests/test_migrations.py`). Runtime `default_login_id` seed verified.

- **SB-1-03 (Backend command endpoint + DB wiring):** Completed — minimal idempotent `POST /api/command` implemented in `backend/app.py`, reads `SESSION_DB` env var, records `command_receipts`, and returns canonical command/result fields.

- **SB-1-04 (Frontend submit path + E2E):** Completed — frontend uses `VITE_BACKEND_URL` or relative `/api/command` and Vite dev proxy configured; end-to-end test `E2E-I1-001` added (`tests/test_e2e_i1_001.py`).

- **SB-1-06 (Validation error mapping and recovery UX):** Completed — implemented structured validation error metadata (`field`), backend now returns `field` on validation errors (e.g., missing `player_name`), frontend surfaces inline field highlights and remediation toasts, and added focused frontend tests. Frontend coverage increased above the 80% baseline (approx. 84.5% after tests). See changes in `backend/errors.py`, `backend/contracts.py`, `backend/app.py`, `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, and `frontend/src/Main.test.tsx`. Commit: 0f2be2d.

Keep this section updated as implementation progresses.

Board import file:
- work-process/design/sprint_board_import_v1.csv

## 11) Testing & CI (new)

This project requires tests and CI checks to be present on all changes. The following automated rules are enforced by convention and CI configuration:

- **Backend tests:** A GitHub Actions workflow runs `pytest` with coverage on `push` and `pull_request` targeting `main`/`master`. Backend tests must pass before merging.
- **PR checklist:** All PRs should include a brief test summary and confirm new/updated tests via the repository PR template.
- **Coverage reporting:** Backend tests produce a coverage XML artifact. Teams should integrate Codecov or similar if desired; the CI will fail on test failures and is configured to expose coverage artifacts for additional checks.
- **Local checks:** Developers should run `pytest -q` locally and ensure migrations and runtime seeds apply (see `work-process/scripts/migrate.py`).
- **Frontend tests:** Add `test` scripts to `frontend/package.json` (use `vitest`/Jest) — the CI job for frontend will run tests if present; teams should add coverage tooling for frontend as they add tests.

Where to find CI config:
- Backend workflow: `.github/workflows/backend-tests.yml`
- PR template: `.github/PULL_REQUEST_TEMPLATE.md`

### Coverage thresholds

We publish coverage to Codecov and enforce a starting baseline of **80%** coverage.

- Config is in `codecov.yml` at the repository root; it sets a project and patch target of 80%.
- To enable enforcement, connect the repository at https://codecov.io and (for private repos) add the `CODECOV_TOKEN` secret in the repository settings. For public repos the token is optional.
- After enabling Codecov you can use the Codecov status checks on branches or configure branch protection to block merges that reduce coverage below the threshold.

If you'd prefer to start with a lower threshold for specific packages or directories, update `codecov.yml` accordingly.

Additions to these files are the recommended live enforcement; keep this section updated if CI configuration changes.

### Pre-commit hooks (local checks)

We provide a `.pre-commit-config.yaml` in the repo to run quick sanity checks and fast unit tests locally before pushing. Recommended local setup:

1. Install `pre-commit` in your Python environment:

```bash
python -m pip install --upgrade pip
pip install pre-commit
```

2. Install the git hooks in your repo:

```bash
pre-commit install
```

3. Run the full pre-commit suite once (optional but recommended):

```bash
pre-commit run --all-files
```

Notes:
- The configured `pytest` hook runs on `push` (so CI-like checks run before pushes). It excludes E2E tests by default (`-k "not e2e"`) to keep local runs quick; edit `.pre-commit-config.yaml` if you want a different policy.
- You can run `pytest` separately or adjust the hook to run on `commit` instead of `push` if you prefer immediate feedback.
