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

The runtime persists only agent ID, tool name, run status/timestamps, SHA-256 digests of input/result, and an error class code. It does not persist raw arguments or tool results. Append-only events record invocation start and completion/failure with a strict metadata allowlist. Each process has a random worker ID; each active run stores that worker ID and a UTC lease expiry. The default lease is 60 seconds and the invocation renews it every 20 seconds while the tool is executing. A worker can renew or finish only while it still owns an unexpired lease. Expired runs are recovered transactionally under SQLite `BEGIN IMMEDIATE` during runtime initialization, before a new invocation starts, and when run history is listed. Only one concurrent worker can record the interrupted transition. Legacy running rows without lease metadata are treated as orphaned and recovered during runtime initialization.

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


## Operational hardening note

Event listing is bounded to 100 records per request, and run completion is accepted only once while the run is in the `running` state. Worker IDs and lease expiry are operational metadata and are excluded from portable workspace schema 1.3.0. Multi-worker support is limited to processes sharing one local SQLite database on a filesystem with reliable SQLite locking. Multi-host deployments, network filesystems, and mixed-version rolling upgrades are unsupported. Stop all application processes before upgrading to the lease-aware version; keep deployment single-process until PR #28 passes review and CI.
