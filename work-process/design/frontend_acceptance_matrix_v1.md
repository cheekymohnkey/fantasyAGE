# Fantasy AGE DM Assistant - Frontend Acceptance Matrix v1

## 1) Purpose

This matrix translates functional requirements (FR) and UX requirements (UR) into screen-level acceptance criteria and test evidence for implementation handoff.

Sources:
- requirements/game_requirements_v1.md
- design/system_design_v1.md
- design/frontend_ux_strategy_v1.md

## 2) Legend

- Priority: P0 (must for MVP), P1 (should for MVP hardening), P2 (post-MVP)
- Evidence: UT (unit test), IT (integration test), UAT (usability acceptance), A11Y (accessibility check), TELE (telemetry verified)

## 3) Screen-to-Requirement Matrix

| Screen | Requirement IDs | Priority | Acceptance Criteria | Evidence |
| --- | --- | --- | --- | --- |
| Session Home | FR-001, FR-015, NFR-002, UR-001 | P0 | Active scene, pending confirmations, and latest action outcomes render within 2s on local profile; blocked/confirm-required items clearly surfaced. | IT, UAT, TELE |
| Campaign and Session Selector | FR-022, FR-023, NFR-004 | P0 | DM can create/list/open/archive campaigns and create/list/open sessions; invalid campaign-session pair blocks actions with clear context guidance. | IT, UAT, TELE |
| Login Context Banner | FR-024, FR-025, NFR-004, NFR-006 | P0 | Active login context is visible; pre-auth default login mode is shown; owner mismatch blocks action with recovery path. | IT, UAT, TELE |
| Exploration Workspace | FR-003, FR-004, NFR-001, NFR-006, UR-001, UR-005 | P0 | DM can resolve an exploration test from command entry to result in <= 8s median; formula summary and citations reachable in one interaction. | IT, UAT, TELE |
| Combat Console | FR-005, FR-006, FR-007, FR-008, FR-009, UR-002, UR-004 | P0 | Initiative, turn action, condition updates, and stunt selection complete in <= 12s median for standard attack flow; illegal stunt attempts show legal alternatives. | IT, UAT, TELE |
| Progression Workspace | FR-010, FR-011, FR-012, FR-015, UR-004 | P0 | Invalid choices are blocked with prerequisite reason; valid choices show stat diff and require confirmation before apply. | IT, UAT |
| Rules Assistant Panel | FR-013, FR-014, FR-016, NFR-006, UR-003, UR-005 | P0 | Strong evidence yields citation-backed answer; weak evidence yields uncertainty label and explicit no-mutation message. | IT, UAT, TELE |
| Audit and Replay View | NFR-002, NFR-004, UR-005 | P1 | Event stream filter and replay entry points available; action details include reason codes, citations, and correlation IDs. | IT, UAT |
| Global Command Bar | FR-001, FR-013, UR-001, UR-004 | P0 | Typeahead supports top command intents; keyboard-only command submission works without context loss after validation errors. | IT, A11Y, UAT |
| Entity Management Flows | FR-017, FR-018, FR-019, FR-020, FR-021, FR-015 | P0 | Canon entity update/delete shows mandatory warning; canon delete requires warning acknowledgment plus second-step confirmation before mutation. | IT, UAT, TELE |

## 4) State and Error Acceptance Matrix

| UI State | Trigger | Required UX Behavior | Requirement IDs | Evidence |
| --- | --- | --- | --- | --- |
| Loading | Command submitted, awaiting result | Show deterministic progress indicator and preserve current context controls where safe. | UR-004 | UAT |
| Validation Error | Missing/invalid input fields | Inline field guidance with reason code mapping; no scene reset. | UR-004, NFR-006 | IT, UAT |
| Policy Block | retrieval.insufficient_evidence or retrieval.conflicting_evidence | Show block card with reason code, affected action, and next-step options; no mutation indicator shown. | FR-016, UR-003 | IT, UAT |
| Confirmation Required | impactful mutation pending | Inline confirmation tray with approve/reject and summary diff preview. | FR-015 | IT, UAT |
| Resolver Error | resolver.* reason codes | Action card displays failure cause and safe retry options; no duplicate submission. | NFR-004, UR-004 | IT |
| Persistence Conflict | persistence.version_conflict | Prompt refresh-and-retry flow with replay-safe messaging. | NFR-004 | IT, UAT |
| Uncertainty Informational | weak evidence on non-state query | Uncertainty banner and explicit no-state-change statement. | FR-014, FR-016 | IT, UAT |
| Canon Mutation Warning | guard.canon_warning_required | Warning modal appears and blocks mutation until explicit acknowledgment. | FR-020, NFR-006 | IT, UAT, A11Y |
| Canon Delete Confirmation | guard.canon_delete_confirmation_required | Second-step confirmation required after warning acknowledgment for delete. | FR-021, FR-015 | IT, UAT |

## 5) Accessibility Acceptance Criteria (WCAG 2.2 AA)

1. Keyboard-only completion for P0 tasks (exploration test, combat attack, progression validation, rules query).
2. All interactive controls have visible focus and ARIA labels.
3. Error and blocked states are announced to screen readers.
4. Color is never the sole indicator for status states.
5. Minimum contrast targets are met across default and high-contrast themes.

Evidence:
- A11Y checklist per screen + automated audit report + manual keyboard walkthrough notes.

## 6) Telemetry Acceptance Criteria

Required events for MVP:
- command_submitted
- action_blocked_viewed
- confirmation_approved
- confirmation_rejected
- citation_opened
- uncertainty_banner_viewed

MVP telemetry gate:
- 100% of P0 flows emit command_submitted and terminal outcome event.
- > 95% of blocked actions emit action_blocked_viewed.

## 7) End-to-End Acceptance Scenarios

Scenario A: Exploration Test with Clue Discovery
- Requirements: FR-003, FR-004, UR-001, UR-005
- Pass when: action resolves in target time, clue state updates, and citation/formula drill-down is reachable.

Scenario B: Combat Turn with Stunt Validation
- Requirements: FR-005, FR-006, FR-008, FR-009, UR-002, UR-004
- Pass when: valid stunt applies and illegal stunt path clearly recovers without state corruption.

Scenario C: Progression Validation and Apply
- Requirements: FR-010, FR-011, FR-012, FR-015
- Pass when: invalid choices are blocked, valid diff preview shown, and confirmation gate enforced.

Scenario D: Informational Rules Query with Weak Evidence
- Requirements: FR-013, FR-014, FR-016, UR-003
- Pass when: uncertainty response shown with explicit no-mutation behavior.

Scenario E: Canon Entity Delete Safeguard
- Requirements: FR-020, FR-021, FR-015
- Pass when: warning modal blocks delete, acknowledgment is captured, and second-step confirmation is required before commit.

## 8) Release Readiness UX Gates

All must be true for v1 UX gate:
1. P0 screen matrix criteria pass.
2. State/error matrix criteria pass.
3. Accessibility checks pass for all P0 workflows.
4. Telemetry events present and validated for P0 workflows.
5. Usability benchmark targets from UR set are met or have approved mitigation waivers.
