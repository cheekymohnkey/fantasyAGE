# Fantasy AGE DM Assistant - Frontend Component Contracts v1

## 1) Purpose

Defines component-level contracts between frontend interactions and backend command/result/error schemas.

Goals:
- Ensure all state-changing actions map to typed command envelopes.
- Normalize error and policy block rendering across screens.
- Keep UI behavior deterministic with backend reason codes.

## 2) Global Envelope Contracts

### 2.1 Command Request (UI -> API)

```json
{
  "action_id": "uuid",
  "campaign_id": "uuid",
  "session_id": "uuid",
  "actor_id": "character_or_dm_id",
  "command_type": "combat.attack",
  "command_payload": {},
  "client_timestamp": "2026-03-20T12:00:00Z",
  "idempotency_key": "uuid-or-stable-key"
}
```

Rules:
- idempotency_key is required for state-changing command types.
- command_payload schema depends on command_type.
- login_id is mandatory; in pre-auth mode it is sourced from configured default login context.

### 2.2 Success Response Envelope

```json
{
  "action_id": "uuid",
  "status": "resolved",
  "action_result": {},
  "formula_trace": {},
  "citations_used": ["chunk_123"],
  "warnings": [],
  "confirmation_required": false,
  "correlation_id": "uuid"
}
```

### 2.3 Error/Block Envelope

```json
{
  "action_id": "uuid",
  "status": "blocked",
  "reason_code": "retrieval.insufficient_evidence",
  "message": "Insufficient evidence for state-changing action",
  "next_steps": ["request_dm_override", "ask_rules_query"],
  "dm_decision_required": true,
  "correlation_id": "uuid"
}
```

Canon mutation warning fields (for `entity.update` and `entity.delete` on canon provenance):
- warning_required: boolean
- warning_id: string
- warning_acknowledged: boolean
- requires_delete_confirmation: boolean

Canonical reason codes:
- validation.missing_field
- validation.invalid_enum
- precondition.scene_mismatch
- precondition.campaign_session_mismatch
- precondition.owner_scope_mismatch
- retrieval.insufficient_evidence
- retrieval.conflicting_evidence
- resolver.illegal_stunt_selection
- resolver.prerequisite_failed
- confirmation.rejected
- persistence.version_conflict
- persistence.transaction_failed
- guard.canon_warning_required
- guard.canon_delete_confirmation_required

## 3) Shared Component Contracts

### 3.1 CommandBar

Props:
- campaignId: string
- sessionId: string
- actorId: string
- allowedCommandTypes: string[]
- onSubmit(commandEnvelope)
- suggestionsProvider(inputText)

Events:
- command_submitted
- command_suggest_selected

Behavior:
- Supports keyboard-only submit and command history recall.
- Preserves typed input on validation failures.
- Blocks submit if campaignId/sessionId binding is invalid in client context.
- Blocks submit if login owner context is missing or mismatched.

### 3.2 ActionResultCard

Props:
- actionId: string
- outcome: string
- summaryText: string
- formulaTrace: object
- citations: string[]
- warnings: string[]
- onOpenEvidence(citationId)

Behavior:
- Always exposes formula/citation drill-down affordance.
- Shows warnings without obscuring final status.

### 3.3 PolicyBlockCard

Props:
- reasonCode: string
- humanMessage: string
- dmDecisionRequired: boolean
- nextSteps: string[]
- onSelectNextStep(step)

Behavior:
- Must render explicit no-mutation indicator for blocked state-changing actions.
- Must include direct action to open evidence details.

### 3.4 ConfirmationTray

Props:
- actionId: string
- requiresConfirmation: boolean
- impactSummary: string
- proposedDiff: object
- onApprove()
- onReject(reason)

Behavior:
- Reject path requires rationale text.
- Approval emits confirmation_approved telemetry event.

### 3.5 EvidenceDrawer

Props:
- citations: Array<{id: string, snippet: string, score?: number}>
- uncertaintyFlag: boolean
- onOpenCitation(id)

Behavior:
- For uncertainty state, highlights missing/conflicting evidence reasons.

### 3.6 CanonMutationWarningModal

Props:
- warningId: string
- entityType: string
- entityId: string
- operation: "update" | "delete"
- warningMessage: string
- requiresDeleteConfirmation: boolean
- onAcknowledge()
- onCancel()

Behavior:
- Must appear before any canon entity update/delete request is committed.
- Delete operation requires second-step confirmation after acknowledgment.
- Emits telemetry event `canon_warning_acknowledged` when accepted.

## 4) Screen-Specific Contracts

### 4.1 Exploration Workspace

Inputs:
- ability: enum
- focusApplied: boolean
- rollTotal: number
- modifiers: object

Command mapping:
- command_type: exploration.test

Result mapping:
- outcome, margin, stunt_points(optional), clue_updates(optional)

### 4.2 Combat Console

Inputs:
- actorId
- targetId
- rollTotal
- stuntDie
- modifiers
- selectedStunts[]

Command mapping:
- command_type: combat.attack

Blocked handling:
- resolver.illegal_stunt_selection -> show legal alternatives list.

### 4.3 Progression Workspace

Command mappings:
- progression.validate
- progression.apply

Required UI rule:
- progression.apply control disabled until valid progression.validate result exists in current correlation chain.

### 4.4 Rules Assistant Panel

Command mapping:
- rules.query

Response handling:
- If uncertainty_flag=true, render uncertainty banner and disable mutation affordances.

### 4.5 Entity Management Flows

Command mapping:
- campaign.create
- campaign.list
- campaign.open
- campaign.archive
- session.create
- session.list
- session.open
- entity.create
- entity.read
- entity.list
- entity.update
- entity.delete

Canon mutation rule:
- If target provenance is canon and command is update/delete, display CanonMutationWarningModal.
- If delete, require additional confirmation after warning acknowledgment.

## 5) Client State Model (Suggested)

Slices:
- sessionSlice: scene mode, active entities, pending confirmations.
- commandSlice: active submission, last response, errors.
- combatSlice: initiative, turn state, selected actions/stunts.
- evidenceSlice: citations, drawer state, uncertainty flags.
- telemetrySlice: client-side emit queue and health.

Rules:
- Server state and UI state are separated.
- Last-known successful result remains visible during transient retries.

## 6) Error-to-UX Mapping Table

| reason_code | UI Surface | Severity | User Guidance |
| --- | --- | --- | --- |
| validation.missing_field | inline form + toast | warning | Highlight required fields and preserve input context. |
| precondition.scene_mismatch | action card | warning | Offer transition to required scene mode. |
| precondition.campaign_session_mismatch | context banner + selector | blocking | Require selecting a valid session for the active campaign before retry. |
| precondition.owner_scope_mismatch | owner context banner | blocking | Require switching to the owning login context before retry. |
| retrieval.insufficient_evidence | policy block card | blocking | Show no-mutation status and DM decision options. |
| retrieval.conflicting_evidence | policy block card + evidence drawer | blocking | Show conflicting citations and ask for DM override path. |
| resolver.illegal_stunt_selection | combat stunt panel | warning | List legal stunt options and maintain selected target/roll context. |
| persistence.version_conflict | modal + retry banner | blocking | Offer refresh/retry with idempotent request handling. |
| guard.canon_warning_required | canon warning modal | blocking | Require explicit warning acknowledgment before canon update/delete can proceed. |
| guard.canon_delete_confirmation_required | confirmation tray | blocking | Require second-step confirmation after warning acknowledgment for canon delete operations. |

Note: Validation error responses MAY include a `field` property when the error is specific to a single input. Example:

```json
{
  "status": "error",
  "reason_code": "validation.missing_field",
  "message": "Missing required field",
  "remediation_hint": "Missing 'player_name'.",
  "field": "player_name"
}
```

Frontend components should prefer `field` when mapping server-side validation to inline inputs; `remediation_hint` should be surfaced in inline and toast contexts as guidance.

## 7) Accessibility Contract by Component

1. CommandBar:
- full keyboard operation, labeled autocomplete, escape-to-close behavior.

2. PolicyBlockCard:
- announced as alert region with clear severity semantics.

3. ConfirmationTray:
- focus trap while open; return focus to triggering control on close.

4. EvidenceDrawer:
- navigable citation list and readable snippet structure for screen readers.

## 8) Contract Testing Guidance

Contract tests required:
1. Command envelope generation per command type.
2. Error mapping correctness for every reason_code.
3. Confirmation gating behavior for impactful actions.
4. Uncertainty rendering behavior for weak-evidence informational responses.

Consumer-driven contract tests:
- Frontend fixtures validated against backend response schemas each CI run.

## 9) Versioning and Change Control

- Contract changes require version bump and migration notes in PR description.
- Additive fields should be backward-compatible by default.
- Breaking changes must include coordinated frontend/backend rollout plan.
