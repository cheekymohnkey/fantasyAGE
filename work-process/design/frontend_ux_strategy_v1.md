# Fantasy AGE DM Assistant - Frontend and UX Strategy v1

## 1) Purpose

This document defines the v1 frontend approach with usability and UX as first-class concerns from project start.

Objectives:
- Make fast, low-friction DM workflows the primary product experience.
- Keep cognitive load low during live session play.
- Ensure mechanical actions are transparent, confirmable, and reversible.

## 2) UX Principles

1. Session speed over visual novelty
- Primary interactions should complete in 1-3 clicks.
- Keyboard-first patterns for frequent in-session actions.

2. Clarity over density
- Surface only essential state by default.
- Move deep detail into drill-down panels.

3. Explainability at action time
- Every resolved action shows inputs, formula summary, and citations.
- Blocked actions explain why and what the DM can do next.

4. Safety for state-changing actions
- High-impact mutations require explicit confirmation.
- Undo is modeled as compensating actions with full audit trail.

5. Progressive disclosure
- Novice DM mode: guided flows and hints.
- Expert DM mode: compact controls and keyboard shortcuts.

## 3) Primary Users and Context

Primary persona:
- Game Master running live sessions with limited attention and time.

Secondary personas:
- Co-GM/assistant tracking combat and quests.
- Campaign archivist reviewing logs and outcomes between sessions.

Usage contexts:
- Live table session (highest pressure, low tolerance for friction).
- Between-session planning and progression updates.

## 4) Information Architecture

Top-level app sections:
- Command Bar (always visible)
- Scene Workspace
- Combat Console
- Quest Tracker
- Character and Progression
- Rules Assistant
- Audit Log
- Settings

Navigation model:
- Persistent left rail for section switching.
- Global command/search bar at top.
- Context panel on right for citations, formula traces, and warnings.

## 5) Core Screen Inventory

1. Session Home
- Active scene summary.
- Pending confirmations.
- Recent actions and unresolved blockers.

2. Exploration Workspace
- Quick test resolution widget.
- Clues/leads board and reveal readiness indicator.
- Scene notes and world flags.

3. Combat Console
- Initiative ladder.
- Active turn card with attack and stunt actions.
- Condition timeline and effect tick controls.

4. Progression Workspace
- Level-up flow with eligibility guardrails.
- Diff summary before apply.
- Confirmation gate for impactful updates.

5. Rules Assistant Panel
- Ask question input with suggested prompts.
- Response card with citation chips and uncertainty indicator.
- Evidence inspector drawer.

6. Audit and Replay View
- Time-ordered event stream.
- Filters by action type, outcome, and actor.
- Replay controls for forensic review.

## 6) Interaction Design Patterns

Command-first interaction:
- All actions can be launched from command bar with smart suggestions.
- Natural language and structured command templates coexist.

Dual-path execution:
- Quick mode: minimal required fields and defaults.
- Advanced mode: full control of modifiers and context.

Confirmation pattern:
- Inline confirmation tray for high-impact actions.
- Required rationale message on rejection paths.

Conflict and uncertainty pattern:
- State-changing block cards with reason codes and next-step options.
- Informational uncertainty banner with explicit no-mutation statement.

## 7) UX Requirements (v1)

UR-001 Task completion speed
- Exploration test resolution in <= 8 seconds median from command entry to result display.

UR-002 Combat turn efficiency
- Standard attack resolution in <= 12 seconds median including stunt selection.

UR-003 Comprehension
- 90%+ of test users can identify why an action was blocked within 5 seconds.

UR-004 Error recovery
- 95%+ of user input errors recoverable without page/context reset.

UR-005 Traceability access
- Citation and formula detail available within one interaction from any resolved action.

UR-006 Accessibility baseline
- WCAG 2.2 AA for color contrast, focus visibility, keyboard navigation, and screen reader labels.

## 8) Accessibility and Inclusivity

Must-have a11y behaviors:
- Full keyboard operation for all core flows.
- Focus order aligned with visual order.
- Proper ARIA labeling on controls, alerts, and dialog states.
- Non-color-only status signaling for success/warn/block states.
- Reduced motion mode honoring system preferences.

Readable presentation:
- Minimum base font sizing and scalable type system.
- High-contrast theme variant in v1.

## 9) Responsive Layout Strategy

Target form factors:
- Desktop first (>= 1280 px) for active session operation.
- Laptop compact mode (1024-1279 px) with collapsible side panels.
- Tablet support (>= 768 px) for assistant/co-GM use.

Layout rules:
- Command bar remains persistent across breakpoints.
- Right context panel collapses into drawer on narrower screens.
- Combat controls keep turn-critical actions visible without scrolling where possible.

## 10) Visual and Component Strategy

Design system approach:
- Build a lightweight tokenized design system early.
- Tokens: color, spacing, typography, elevation, motion, and state semantics.

Component priority list:
- Command input with typeahead
- Action card
- Confirmation tray/modal
- Initiative list
- Condition chips and timers
- Citation chip + evidence drawer
- Diff viewer
- Event timeline row

Content style:
- DM-facing concise language.
- Avoid ambiguous wording on blocked actions.
- Standardized reason-code to human message mapping.

## 11) Frontend Technical Approach

Recommended v1 stack:
- React + TypeScript + Vite
- State: Zustand or Redux Toolkit (event-driven slices)
- Data fetching/cache: TanStack Query
- Forms/validation: React Hook Form + schema validation
- Component baseline: headless primitives with custom styling tokens

Architecture:
- Feature-based frontend modules aligned with backend action categories.
- API client generated or strongly typed from shared contracts.
- UI state separated from server state and replay state.

Performance practices:
- Virtualize long event/audit lists.
- Use optimistic UI only for non-critical read interactions.
- No optimistic mutation confirmation for state-changing mechanics.

## 12) UX Research and Validation Plan

Discovery sprint outputs:
- Low-fidelity wireframes for six core screens.
- Task flow maps for exploration, combat, progression, and rules query.

Usability testing cadence:
- Round 1: 5-7 GM users on clickable prototype.
- Round 2: 8-10 GM users on integrated alpha.

Measured tasks:
- Resolve exploration test.
- Run one full combat turn with condition and stunt.
- Ask rules question and evaluate confidence/citation understanding.
- Complete level-up validation and apply.

Success thresholds:
- System Usability Scale >= 78 by end of alpha.
- Critical task success rate >= 90% without facilitator intervention.

## 13) Telemetry and Product Analytics

Instrumented frontend events:
- command_submitted
- command_suggest_selected
- action_blocked_viewed
- confirmation_approved and confirmation_rejected
- citation_opened
- uncertainty_banner_viewed
- undo_requested

UX dashboards:
- Time-to-resolution by action type.
- Block reason frequency.
- Confirmation reject rate.
- Error recovery funnel.

## 14) Frontend Delivery Phases

Phase UX-0: Foundation (parallel with backend Milestone 0)
- UX principles finalized.
- Wireframes and interaction specs.
- Design tokens and component primitives.

Phase UX-1: Live Session Core (parallel with Milestones 1-3)
- Session Home, Exploration Workspace, Combat Console.
- Command bar and confirmation patterns.

Phase UX-2: Progression and Rules Experience (parallel with Milestones 4-5)
- Progression Workspace and Rules Assistant improvements.
- Evidence drawer and uncertainty treatments.

Phase UX-3: Hardening (parallel with Milestone 6)
- Accessibility remediation.
- Performance optimization.
- Analytics tuning and usability retest.

## 15) Handoff Requirements to Engineering

Required implementation artifacts:
- Screen-level interaction specs with empty/loading/error/blocked states.
- Component contracts mapped to backend action and error schemas.
- Keyboard shortcut map for high-frequency operations.
- Copy deck for reason-code messages and confirmation prompts.

Definition of UX-ready story:
- Acceptance criteria includes usability and accessibility checks.
- Instrumentation events defined.
- Edge states documented.

Companion implementation artifacts:
- frontend acceptance matrix: work-process/design/frontend_acceptance_matrix_v1.md
- frontend component contracts: work-process/design/frontend_component_contracts_v1.md
- frontend prioritized backlog: work-process/design/frontend_backlog_v1.md

## 16) Risks and Mitigations

Risk 1: Command complexity overwhelms new users.
- Mitigation: guided templates, inline examples, progressive disclosure.

Risk 2: Combat UI becomes too dense under pressure.
- Mitigation: turn-focused layout, collapsible secondary data, keyboard shortcuts.

Risk 3: Uncertainty and block states reduce trust.
- Mitigation: clear reason codes, next steps, and visible evidence access.

Risk 4: Accessibility deferred too late.
- Mitigation: WCAG checks in Definition of Done from first UI sprint.
