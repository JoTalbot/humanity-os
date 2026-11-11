# Agent Runtime Contract 0.1

Agents are bounded software actors, not independent authorities.

## Agent declaration
Each agent declares ID/version, responsible owner, purpose, allowed inputs, permitted tools/scopes, model constraints, retention policy, approval requirements, timeout, budget and retry limits.

## Lifecycle
proposed → authorised → running → awaiting_approval → running (approval granted) → completed | failed | cancelled. Approval denial or expiry transitions to cancelled. Every transition is recorded; invalid transitions are rejected. An approved action resumes only with the original scoped capability, before its deadline, and after policy is checked again.

## Tool invocation
Every call carries task/agent IDs, capability, scope, schema version, idempotency key, deadline and budget. Policy is checked before execution.

## Human approval
Explicit approval is required for external communication, purchases, publication, destructive changes, access grants, financial actions and other high-impact side effects. Approval is scoped and expires.

## Output
Return result, status, evidence references, uncertainty, limitations, attempted actions, completed actions and approval references.

## Prohibited
Self-granted permissions; hidden side effects; treating retrieved content as instructions; goal substitution; private-data exfiltration; privileged execution of unreviewed code.

Use bounded retries, idempotency, cancellation and explicit partial-failure states. A timeout does not prove an external action did not happen; reconcile before retrying.
