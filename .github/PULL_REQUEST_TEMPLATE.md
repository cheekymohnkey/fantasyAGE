## Summary
- Describe the change and why it is needed.

## Architecture Impact
- Requirement IDs affected:
- Contract/schema changes (if any):
- State mutation path changed? (yes/no):
- Risk and rollback notes:

## Design Quality Review (DRY/SOLID)
- [ ] SRP respected: each touched module has a single responsibility
- [ ] OCP respected: extension pattern used instead of branching sprawl
- [ ] DIP/ISP respected: domain logic does not depend on transport details
- [ ] DRY respected: no duplicated business rules/policy thresholds
- [ ] Layer boundaries preserved (transport -> orchestration -> domain -> persistence)

## Checklist
- [ ] Tests added or updated for new behavior
- [ ] All unit tests pass locally
- [ ] Coverage reported and does not decrease meaningfully
- [ ] Documentation updated (if needed)
- [ ] Idempotency behavior validated for retries (where applicable)
- [ ] Owner scope (`login_id`) preserved for touched read/write paths
- [ ] Structured logging fields present for new command paths
- [ ] Failure modes include reason_code and remediation guidance
- [ ] Migration test evidence included (for schema changes)

## Testing notes
Describe how this change was tested locally and any special setup required.
