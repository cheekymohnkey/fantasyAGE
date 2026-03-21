# SB-1-05 — Persist no-op command event and display summary in Session Home

Status: Ready (creating task breakdown)

Owner: frontend/backend

Target: ensure a no-op command submitted from the frontend is persisted and displayed in Session Home; verify via E2E `E2E-I1-001`.

## Acceptance Criteria
- Frontend can POST a no-op command to `POST /api/command` with `login_id`/`campaign_id`/`session_id` in `metadata`.
- Backend persists a `command_receipt` / event row in SQLite with correct owner scoping (`login_id`).
- Session Home lists the persisted event summary (id, action_id, timestamp, short result) without exposing internal stack traces.
- E2E `E2E-I1-001` passes locally and in CI.

## Sub-tasks
- Backend: ensure persistence and owner scoping
  - [x] Verify `backend/app.py` `POST /api/command` persists `command_receipts` including `metadata.login_id`, `campaign_id`, `session_id`.
  - [x] Add/adjust DB query to return the persisted receipt for Session Home API (e.g., `GET /api/sessions/{session_id}/events`).
  - [x] Add unit tests for persistence and owner scoping (integration-style DB test).

- Frontend: submit and display
  - [x] Add submit UI in Session Home to send the no-op command (use existing form/button patterns).
  - [x] Implement fetch to `GET /api/sessions/{session_id}/events` and render event summary list.
  - [x] Add focused frontend tests (vitest/React Testing Library) asserting submission path and rendering.

- Tests / E2E
  - [ ] Enable and run `tests/test_e2e_i1_001.py` locally; update fixtures if needed.
  - [ ] Add CI step to run E2E (if desired) or keep gated under specific label.

- PR / Documentation
  - [ ] Create PR referencing this task and include a short test summary.
  - [ ] Update handover `work-process/design/handover.md` with progress notes when merged.

## Quick dev checklist
- Run migrations (if DB changes): `python work-process/scripts/migrate.py`
- Run backend tests: `pytest tests/test_command_endpoint.py -q`
- Run frontend tests: `cd frontend && npm test`

---
Created by automation to capture SB-1-05 sub-tasks and PR checklist.
