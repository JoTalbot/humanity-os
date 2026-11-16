# Agent Runtime Process-Safe Lease Design

Status: implementation design for issue #27

## Intent

Allow multiple application processes on one host to share the same SQLite workspace without one process treating another process's live agent invocation as interrupted. Preserve the explicit, constrained, one-tool-per-owner-request runtime.

## Goals

- Give each process a unique worker identity.
- Assign every running invocation a time-bounded lease.
- Renew the lease while a tool is executing.
- Recover only leases that have expired.
- Make recovery and terminal transitions atomic under SQLite write locking.
- Reject completion or failure from a worker that no longer owns a valid lease.
- Preserve existing event types and schema 1.3.0 export compatibility.

## Non-goals and limits

- No multi-host/distributed deployment or network-filesystem guarantee.
- No OS sandbox, autonomous agent loop, arbitrary tool execution, or new external side effects.
- No change to tool allowlists, one-tool-per-request, bounded inputs/results, or owner approval of durable memory.
- Lease ownership does not roll back a local tool side effect that completed just before lease loss. Current write-capable tool only creates a pending-review memory proposal.

## Approaches

1. **Process-wide advisory lock:** simple, but prevents useful parallel workers and does not identify/recover individual runs. Rejected.
2. **Per-run lease with heartbeat:** process identity plus expiry on each run, renewed during invocation; stale runs recovered transactionally. Selected because it supports multiple workers while fencing stale owners.
3. **External coordination service:** stronger cross-host coordination but adds infrastructure and dependencies that do not fit the local-first SQLite prototype. Deferred.

## Contract

- Each `AgentRuntimeStore` instance receives a random UUID worker ID unless one is injected for tests.
- Default lease duration is 60 seconds; the runtime renews at one-third of that duration (20 seconds).
- All persisted timestamps are timezone-aware UTC ISO-8601 values.
- A run is owned only while status is `running`, `worker_id` matches, and `lease_expires_at` is strictly later than the operation time.
- Lease renewal and terminal transitions are conditional writes. A lost/expired lease raises a dedicated `AgentRunLeaseLost` error.
- Recovery runs inside `BEGIN IMMEDIATE`; it updates only rows whose lease is null (legacy) or expired at the supplied UTC time. Conditional updates ensure exactly one recovery event.
- Legacy running rows without lease metadata are considered orphaned and recoverable immediately after upgrade. Upgrade all workers together; mixed old/new application processes are unsupported.
- Worker ID and lease expiry are operational coordination metadata and are excluded from workspace exports. Imported running rows have no valid live owner and are recovered on runtime initialization.
- Heartbeat failure stops the invocation from reporting success. A stale worker cannot append a terminal event after lease loss.
- Multi-worker support is limited to processes sharing one local SQLite database on a filesystem with reliable SQLite locking. Keep one process until the implementation and concurrency tests pass.

## Data changes

Add nullable `worker_id` and `lease_expires_at` columns to `agent_runs`, plus an index on `status, lease_expires_at`. Existing schema 1.3.0 export columns remain unchanged.

## Verification

Tests must cover live-run preservation on second-worker startup, lease renewal, stale-owner fencing, exactly-once concurrent recovery, legacy schema migration, and existing run/event export-import compatibility. Full CI must pass before multi-worker support is declared.
