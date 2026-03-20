# Fantasy AGE DM Assistant - Frontend UX Backlog v1

## 1) Purpose

Prioritized UX delivery backlog with epics and implementation-ready stories aligned to MVP scope.

## 2) Prioritization Framework

- P0: required for MVP release
- P1: high-value hardening for MVP stability/usability
- P2: post-MVP improvements

Scoring dimensions used:
- user impact
- session criticality
- implementation dependency
- risk reduction

## 3) Epic Map

Epic FE-01 (P0): Command-Centric Session Shell
- Goal: Fast global command workflow with resilient state and error handling.

Epic FE-02 (P0): Exploration Workspace UX
- Goal: Resolve tests and manage clues/leads with minimal friction.

Epic FE-03 (P0): Combat Console UX
- Goal: Turn-critical, low-latency combat interaction with stunt and condition flows.

Epic FE-04 (P0): Progression Workspace UX
- Goal: Safe level-up validation/apply with diff visibility.

Epic FE-05 (P0): Rules Assistant UX
- Goal: Citation-first answers with uncertainty and non-mutation clarity.

Epic FE-06 (P1): Audit, Replay, and Forensics UX
- Goal: Inspect and replay event history efficiently.

Epic FE-07 (P1): Accessibility and Responsive Hardening
- Goal: WCAG 2.2 AA compliance and compact layout quality.

Epic FE-08 (P1): UX Telemetry and Insights
- Goal: Instrumentation and dashboards for iteration.

Epic FE-09 (P0): Entity CRUD and Canon Safety UX
- Goal: Complete create/read/update/delete flows for runtime and canon-tagged entities with mandatory warning safeguards.

## 4) P0 Stories (Implementation Ready)

### FE-01: Command-Centric Session Shell

1. FE-01-01 Global command bar with typeahead
- Acceptance:
  - supports keyboard-only submit.
  - emits command_submitted telemetry.
  - preserves input on validation error.
- Dependencies: backend command envelope contract.

2. FE-01-02 Session home status strip
- Acceptance:
  - shows active scene, pending confirmations, and latest block state.
  - refreshes without full page reset.
- Dependencies: session summary endpoint.

3. FE-01-03 Standard error surface framework
- Acceptance:
  - reason_code mapped to consistent UI treatment.
  - retry path present for recoverable errors.
- Dependencies: reason_code schema.

### FE-02: Exploration Workspace UX

1. FE-02-01 Exploration test widget
- Acceptance:
  - ability/focus/modifier inputs available.
  - median completion <= 8 seconds in usability run.
- Dependencies: exploration.test command.

2. FE-02-02 Clue and lead board
- Acceptance:
  - clue discovery updates render in-line with action result.
  - reveal readiness state visible.
- Dependencies: quest/clue state contract.

### FE-03: Combat Console UX

1. FE-03-01 Initiative ladder and active turn card
- Acceptance:
  - active actor is visually and semantically highlighted.
  - turn-critical controls remain visible in compact layout.
- Dependencies: encounter state contract.

2. FE-03-02 Attack and stunt flow
- Acceptance:
  - valid stunt selection completes within standard turn budget.
  - illegal stunt reason shows legal alternatives.
- Dependencies: combat.attack result + reason codes.

3. FE-03-03 Condition chips and effect timers
- Acceptance:
  - apply/tick/clear actions are available with clear timing labels.
  - no ambiguous status color-only indicators.
- Dependencies: condition resolver outputs.

### FE-04: Progression Workspace UX

1. FE-04-01 Progression validation panel
- Acceptance:
  - invalid choices display prerequisite failures.
  - progression.apply disabled until progression.validate passes.
- Dependencies: progression.validate contract.

2. FE-04-02 Diff preview and confirmation tray
- Acceptance:
  - stat delta summary visible pre-commit.
  - confirmation approved/rejected telemetry emitted.
- Dependencies: confirmation flow contract.

### FE-05: Rules Assistant UX

1. FE-05-01 Citation response cards
- Acceptance:
  - every grounded response includes citation chips.
  - citation drawer opens with evidence snippets.
- Dependencies: citations payload.

2. FE-05-02 Uncertainty treatment
- Acceptance:
  - weak evidence responses display uncertainty banner.
  - explicit no-state-mutation statement shown.
- Dependencies: uncertainty flag and failure policy output.

### FE-09: Entity CRUD and Canon Safety UX

1. FE-09-01 Entity CRUD console
- Acceptance:
  - supports create/read/update/delete for Character, Adversary, EncounterState, and Quest.
  - list/read supports status and updated_at filtering.
- Dependencies: entity.create/read/list/update/delete contracts.

2. FE-09-02 Canon update warning flow
- Acceptance:
  - update on canon provenance always opens warning modal.
  - mutation remains blocked until explicit acknowledgment.
- Dependencies: guard.canon_warning_required reason code and warning fields.

3. FE-09-03 Canon delete double-confirmation flow
- Acceptance:
  - delete on canon provenance requires warning acknowledgment and second-step confirmation.
  - cancel at either step leaves entity unchanged.
- Dependencies: guard.canon_delete_confirmation_required reason code and confirmation contract.

## 5) P1 Stories

1. FE-06-01 Event stream filters and timeline virtualization
2. FE-06-02 Replay launcher and correlation trace view
3. FE-07-01 Full keyboard accessibility sweep
4. FE-07-02 High-contrast theme implementation
5. FE-07-03 Tablet compact layout optimization
6. FE-08-01 UX telemetry dashboard and alert thresholds

## 6) Story Sequencing (Recommended)

Sprint 1:
- FE-01-01, FE-01-03, FE-02-01, FE-05-02

Sprint 2:
- FE-01-02, FE-03-01, FE-03-02, FE-05-01

Sprint 3:
- FE-02-02, FE-03-03, FE-04-01, FE-04-02

Sprint 4:
- FE-06-01, FE-06-02, FE-07-01, FE-08-01

## 7) UX Definition of Done Addendum

A story is done only if all apply:
1. Acceptance criteria pass in demo environment.
2. Accessibility checks pass for new interactions.
3. Telemetry events are emitted and verified.
4. Error/blocked/confirmation states are implemented where relevant.
5. Linked requirement IDs are updated in story metadata.

## 8) Dependencies and Risks

Critical dependencies:
- Stable command/result/error contracts from backend.
- Reason code catalog freeze for MVP.
- Availability of citation payload and uncertainty flags.

Top risks:
- Backend contract churn causing UI rework.
- Dense combat interactions reducing usability under pressure.
- Accessibility debt accumulating late in delivery.

Mitigations:
- Consumer-driven contract tests and versioned API schemas.
- Early usability testing on combat flows.
- Enforce accessibility checks in each sprint definition of done.
