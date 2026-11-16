# Agent Runtime Leases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Agent Runtime run ownership, renewal, completion and crash recovery safe for multiple processes sharing one local SQLite database.

**Architecture:** Add a per-process worker UUID and per-run UTC lease expiry. Renew leases during invocation; use SQLite `BEGIN IMMEDIATE` and conditional updates for recovery and terminal transitions. Keep coordination columns out of portable workspace schema 1.3.0.

**Tech Stack:** Python 3.11+, sqlite3, threading, datetime, pytest, existing FastAPI application.

**Spec:** `docs/superpowers/specs/2026-11-16-agent-runtime-leases-design.md`

## Global Constraints

- Preserve explicit owner-triggered, one-tool-per-request execution.
- Preserve static tool allowlists, bounded arguments/results, pending-review-only memory proposals, and append-only audit events.
- Do not add shell, arbitrary Python, unrestricted filesystem/network access, autonomous loops, or implicit approval.
- No multi-host/network-filesystem guarantees; only same-host processes sharing local SQLite.
- Keep workspace export schema at 1.3.0 and omit worker/lease coordination fields.
- Do not merge, release, or deploy.

## Review Focus

- A second worker starts while a valid run is active: it must leave the run untouched.
- Two workers recover the same expired run concurrently: exactly one may transition it.
- A stale worker finishes after lease expiry or reassignment: it must not write a terminal event.
- Heartbeat renewal races with expiry/recovery: only a still-valid owner may renew.
- A pre-upgrade database has running rows without lease columns: migration must recover them without corrupting audit history.

---

### Task 1: Lease schema and atomic store lifecycle

**Files:**
- Modify: `src/humanity_os/agent_runtime.py`
- Test: `tests/test_agent_runtime.py`

**Interfaces:**
- `AgentRuntimeStore(database_path, worker_id=None, lease_duration_seconds=60)`
- `start_run(agent_id, tool_name, input_digest, now=None) -> str`
- `renew_run_lease(run_id, now=None) -> None`
- `recover_expired_runs(now=None) -> int`
- `finish_run(run_id, *, result_digest=None, error_code=None, now=None) -> None`
- `AgentRunLeaseLost(RuntimeError)`

- [ ] Write tests for second-worker startup preserving a live lease, stale owner fencing, lease renewal, legacy column migration, and exactly-once concurrent recovery.
- [ ] Run the focused test file and confirm the new behavior fails for the expected reasons.
- [ ] Add nullable coordination columns and index; migrate existing databases safely.
- [ ] Implement worker-owned lease creation, renewal, atomic expired-run recovery, and owner-fenced terminal updates.
- [ ] Run focused tests, then the full pytest suite.

### Task 2: Heartbeat lifecycle during tool invocation

**Files:**
- Modify: `src/humanity_os/agent_runtime.py`
- Modify: `src/humanity_os/app.py`
- Test: `tests/test_agent_runtime.py`

**Interfaces:**
- `AgentRuntimeLeaseLost` is exposed as HTTP 409 (or use the store's dedicated lease exception directly).
- Heartbeat runs in a daemon thread at one-third of the configured lease duration and is stopped/joined before terminal completion.

- [ ] Add a test proving an invocation renews its lease while the tool call is blocked beyond one lease interval.
- [ ] Run that test and confirm it fails before heartbeat implementation.
- [ ] Add heartbeat start/stop, lost-lease propagation, and HTTP 409 mapping without changing tool capabilities.
- [ ] Run focused tests and the full pytest suite.

### Task 3: Compatibility, documentation and release gates

**Files:**
- Modify: `docs/AGENT_RUNTIME.md`
- Modify: `docs/RELEASE_READINESS.md`
- Modify: `docs/INTEGRATION_PLAN_HUMANITY_ONE_0.1.md`
- Test: `tests/test_agent_runtime.py`, existing workspace export/import tests

- [ ] Add assertions that worker IDs and lease timestamps are excluded from schema 1.3.0 exports and imported active runs recover safely.
- [ ] Verify old schema 1.0.0–1.2.0 import compatibility remains unchanged.
- [ ] Document single-host/local-SQLite limits, stop-the-world upgrade requirement, lease defaults, and recovery semantics.
- [ ] Run the complete CI-equivalent suite and inspect the resulting diff.
- [ ] Record remaining security review and deployment restrictions; do not enable multi-worker deployment until all checks pass.
