# Constrained Local Agent Runtime 0.1

## Design

The initial Agent Runtime is a capability registry and one-tool invocation boundary. An owner explicitly submits each invocation through an authenticated API request. There is no background scheduler, autonomous loop, model-driven tool planner, or automatic chain of tool calls.

Built-in profiles:

- \`researcher\`: \`knowledge.search\`, \`documents.search\`, \`documents.context\`.
- \`curator\`: \`documents.search\`, \`documents.context\`, \`memory.propose\`.

The tool catalog classifies each capability by risk and side effects. Unknown agents, unknown tools, and tools not granted to a profile are denied.

## Tool boundary

| Tool | Capability | Effect |
|---|---|---|
| \`knowledge.search\` | Read local owner knowledge | Read-only, bounded summaries |
| \`documents.search\` | Search local text/Markdown chunks | Read-only, bounded source excerpts |
| \`documents.context\` | Prepare source-cited context | Read-only, local-only |
| \`memory.propose\` | Create a memory proposal | Writes only \`pending_review\`; owner approval remains separate |

No shell, arbitrary Python, filesystem browsing/writes, network fetch, credential access, provider activation, external integration, memory approval, or permission escalation tool exists.

## Input/output and audit

Tool arguments are capped at 20,000 UTF-8 bytes. Search limits, context limits, and memory fields have additional per-tool bounds. Results are capped at 20,000 serialized bytes. Knowledge search returns bounded excerpts.

The runtime persists only agent ID, tool name, run status/timestamps, SHA-256 digests of input/result, and an error class code. It does not persist raw arguments or tool results. Append-only events record invocation start and completion/failure with a strict metadata allowlist. A run left in \`running\` after a process interruption is marked failed with \`interrupted\` on the next application startup.

Agent runs and events are included in workspace export schema 1.3.0. Import validates run/event linkage and rejects event details outside the metadata allowlist. Legacy workspace schemas 1.0.0–1.2.0 remain importable with empty agent audit tables.

## API

- \`GET /v1/agents\`
- \`GET /v1/agents/tools?agent_id=researcher\`
- \`POST /v1/agents/{agent_id}/invoke\` with \`tool_name\` and an \`arguments\` object
- \`GET /v1/agents/runs\`
- \`GET /v1/agents/events?run_id=...\`

Every endpoint uses the existing authentication boundary. The UI exposes a manual one-tool runner. The curator can submit a pending memory proposal but cannot approve it.

## Limits

This is not yet an autonomous AI agent platform. It does not generate plans, call a model, execute multi-step workflows, run tools in an OS sandbox, or handle external side effects. Tool allowlists reduce capability but do not replace process isolation or independent security review.
