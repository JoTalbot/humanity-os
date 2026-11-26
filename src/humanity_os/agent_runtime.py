"""Constrained local agent runtime with explicit capability allowlists."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from humanity_os.documents import DocumentStore
from humanity_os.memory import MemoryStore
from humanity_os.store import KnowledgeStore


class SearchToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=10)


class ContextToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=200)
    passage_limit: int = Field(default=5, ge=1, le=10)
    max_context_chars: int = Field(default=4_000, ge=512, le=8_000)


class MemoryProposalToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)
    rationale: str = Field(min_length=1, max_length=2_000)
    source_document_id: str | None = Field(default=None, max_length=128)
    source_chunk_id: str | None = Field(default=None, max_length=128)


AGENT_PROFILES = {
    "researcher": {
        "id": "researcher",
        "name": "Local Researcher",
        "description": "Searches owner knowledge and source documents; does not write durable memory.",
        "tools": ["knowledge.search", "documents.search", "documents.context"],
    },
    "curator": {
        "id": "curator",
        "name": "Memory Curator",
        "description": "Reviews source material and may create pending memory proposals only.",
        "tools": ["documents.search", "documents.context", "memory.propose"],
    },
}


TOOL_CATALOG = {
    "knowledge.search": {
        "description": "Search local owner knowledge records.",
        "risk": "read_only",
        "side_effects": False,
        "requires_separate_approval": False,
    },
    "documents.search": {
        "description": "Search local text and Markdown source chunks.",
        "risk": "read_only",
        "side_effects": False,
        "requires_separate_approval": False,
    },
    "documents.context": {
        "description": "Prepare a bounded source-cited local context packet.",
        "risk": "read_only",
        "side_effects": False,
        "requires_separate_approval": False,
    },
    "memory.propose": {
        "description": "Create a pending memory proposal; cannot approve or activate it.",
        "risk": "pending_owner_review",
        "side_effects": True,
        "requires_separate_approval": True,
    },
}


class AgentRunLeaseLost(RuntimeError):
    """Raised when a worker no longer owns a live agent run lease."""


class AgentRuntimeStore:
    """Persist minimal run metadata and append-only invocation events."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        worker_id: str | None = None,
        lease_duration_seconds: float = 60,
    ) -> None:
        if isinstance(lease_duration_seconds, bool):
            raise ValueError("Agent run lease duration must be a finite positive number")
        try:
            lease_duration = float(lease_duration_seconds)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                "Agent run lease duration must be a finite positive number"
            ) from exc
        if not math.isfinite(lease_duration) or lease_duration <= 0:
            raise ValueError("Agent run lease duration must be a finite positive number")
        self.database_path = str(database_path)
        self._process_id = os.getpid()
        self.worker_id = worker_id or str(uuid4())
        self.lease_duration_seconds = lease_duration
        self.heartbeat_interval_seconds = max(0.01, self.lease_duration_seconds / 3)
        with self._connect() as connection:
            # Serialize first-start and legacy-schema migration across workers.
            # Without a write lock, two processes can both observe missing
            # columns and race the same ALTER TABLE statements.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    input_digest TEXT NOT NULL,
                    result_digest TEXT,
                    error_code TEXT,
                    worker_id TEXT,
                    lease_expires_at TEXT
                )"""
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(agent_runs)")
            }
            if "worker_id" not in columns:
                connection.execute("ALTER TABLE agent_runs ADD COLUMN worker_id TEXT")
            if "lease_expires_at" not in columns:
                connection.execute("ALTER TABLE agent_runs ADD COLUMN lease_expires_at TEXT")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES agent_runs(id),
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    details TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS agent_events_no_update
                   BEFORE UPDATE ON agent_events
                   BEGIN SELECT RAISE(ABORT, 'agent events are append-only'); END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS agent_events_no_delete
                   BEFORE DELETE ON agent_events
                   BEGIN SELECT RAISE(ABORT, 'agent events are append-only'); END"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_runs_started "
                "ON agent_runs(started_at DESC, id DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_runs_lease "
                "ON agent_runs(status, lease_expires_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_events_run "
                "ON agent_events(run_id, occurred_at, id)"
            )
        # Old rows have no owner or expiry and are therefore orphaned.
        self.recover_expired_runs()

    def _connect(self) -> sqlite3.Connection:
        current_process_id = os.getpid()
        if current_process_id != self._process_id:
            # A preloaded application may be forked after store construction.
            # Never let parent and child processes share a lease ownership token.
            self._process_id = current_process_id
            self.worker_id = str(uuid4())
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _timestamp(value: datetime | None = None) -> datetime:
        result = value or datetime.now(UTC)
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("Agent run timestamps must include a timezone")
        return result.astimezone(UTC)

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        run_id: str,
        event_type: str,
        occurred_at: str,
        details: dict,
    ) -> None:
        connection.execute(
            """INSERT INTO agent_events(id, run_id, event_type, occurred_at, details)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(uuid4()),
                run_id,
                event_type,
                occurred_at,
                json.dumps(details, ensure_ascii=False, sort_keys=True),
            ),
        )

    def start_run(
        self,
        agent_id: str,
        tool_name: str,
        input_digest: str,
        *,
        now: datetime | None = None,
    ) -> str:
        started = self._timestamp(now)
        self.recover_expired_runs(now=started)
        started_at = started.isoformat()
        lease_expires_at = (
            started + timedelta(seconds=self.lease_duration_seconds)
        ).isoformat()
        run_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO agent_runs(
                    id, agent_id, tool_name, status, started_at, input_digest,
                    worker_id, lease_expires_at
                ) VALUES (?, ?, ?, 'running', ?, ?, ?, ?)""",
                (
                    run_id,
                    agent_id,
                    tool_name,
                    started_at,
                    input_digest,
                    self.worker_id,
                    lease_expires_at,
                ),
            )
            self._append_event(
                connection,
                run_id,
                "tool_invocation_started",
                started_at,
                {"agent_id": agent_id, "tool_name": tool_name},
            )
        return run_id

    def renew_run_lease(
        self, run_id: str, *, now: datetime | None = None
    ) -> None:
        renewed_at = self._timestamp(now)
        timestamp = renewed_at.isoformat()
        lease_expires_at = (
            renewed_at + timedelta(seconds=self.lease_duration_seconds)
        ).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE agent_runs SET lease_expires_at = ?
                   WHERE id = ? AND status = 'running' AND worker_id = ?
                   AND lease_expires_at > ?""",
                (lease_expires_at, run_id, self.worker_id, timestamp),
            )
            if cursor.rowcount != 1:
                raise AgentRunLeaseLost(
                    "Agent run lease is expired or owned by another worker"
                )

    @contextmanager
    def owned_lease_transaction(self, run_id: str):
        """Hold SQLite's write lock while committing a side effect for a live lease.

        The lease is renewed inside the same transaction before the caller's
        side effect. Recovery and competing workers cannot pass this write lock
        until the side effect commits or rolls back.
        """
        renewed_at = self._timestamp()
        timestamp = renewed_at.isoformat()
        lease_expires_at = (
            renewed_at + timedelta(seconds=self.lease_duration_seconds)
        ).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE agent_runs SET lease_expires_at = ?
                   WHERE id = ? AND status = 'running' AND worker_id = ?
                   AND lease_expires_at > ?""",
                (lease_expires_at, run_id, self.worker_id, timestamp),
            )
            if cursor.rowcount != 1:
                raise AgentRunLeaseLost(
                    "Agent run lease is expired or owned by another worker"
                )
            yield connection

    def recover_expired_runs(self, *, now: datetime | None = None) -> int:
        recovered_at = self._timestamp(now).isoformat()
        recovered = 0
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            candidates = connection.execute(
                """SELECT id FROM agent_runs
                   WHERE status = 'running'
                   AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
                   ORDER BY started_at, id""",
                (recovered_at,),
            ).fetchall()
            for row in candidates:
                cursor = connection.execute(
                    """UPDATE agent_runs SET status = 'failed', finished_at = ?,
                       error_code = 'interrupted'
                       WHERE id = ? AND status = 'running'
                       AND (lease_expires_at IS NULL OR lease_expires_at <= ?)""",
                    (recovered_at, row["id"], recovered_at),
                )
                if cursor.rowcount != 1:
                    continue
                self._append_event(
                    connection,
                    row["id"],
                    "tool_invocation_failed",
                    recovered_at,
                    {"status": "failed", "error_code": "interrupted"},
                )
                recovered += 1
        return recovered

    def finish_run(
        self,
        run_id: str,
        *,
        result_digest: str | None = None,
        error_code: str | None = None,
        now: datetime | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        if connection is not None:
            self._finish_run(
                connection,
                run_id,
                result_digest=result_digest,
                error_code=error_code,
                now=now,
            )
            return
        with self._connect() as active_connection:
            self._finish_run(
                active_connection,
                run_id,
                result_digest=result_digest,
                error_code=error_code,
                now=now,
            )

    def _finish_run(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        *,
        result_digest: str | None = None,
        error_code: str | None = None,
        now: datetime | None = None,
    ) -> None:
        finished_at = self._timestamp(now).isoformat()
        status = "failed" if error_code else "completed"
        cursor = connection.execute(
            """UPDATE agent_runs SET status = ?, finished_at = ?,
               result_digest = ?, error_code = ?
               WHERE id = ? AND status = 'running' AND worker_id = ?
               AND lease_expires_at > ?""",
            (
                status,
                finished_at,
                result_digest,
                error_code,
                run_id,
                self.worker_id,
                finished_at,
            ),
        )
        if cursor.rowcount != 1:
            row = connection.execute(
                "SELECT status, worker_id, lease_expires_at, error_code "
                "FROM agent_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Agent run is missing or already finished")
            if row["status"] != "running":
                if row["status"] == "failed" and row["error_code"] == "interrupted":
                    raise AgentRunLeaseLost(
                        "Agent run lease expired and the run was recovered"
                    )
                raise ValueError("Agent run is missing or already finished")
            raise AgentRunLeaseLost(
                "Agent run lease is expired or owned by another worker"
            )
        self._append_event(
            connection,
            run_id,
            "tool_invocation_failed" if error_code else "tool_invocation_completed",
            finished_at,
            {"status": status, "error_code": error_code},
        )

    def list_runs(
        self, limit: int = 50, *, now: datetime | None = None
    ) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("Agent run limit must be between 1 and 100")
        self.recover_expired_runs(now=now)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM agent_runs ORDER BY started_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_events(self, run_id: str | None = None, limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("Agent event limit must be between 1 and 100")
        with self._connect() as connection:
            if run_id is None:
                rows = connection.execute(
                    "SELECT * FROM agent_events ORDER BY occurred_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM agent_events WHERE run_id = ? ORDER BY occurred_at, id LIMIT ?",
                    (run_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]


class AgentRuntime:
    """Invoke one allowlisted local tool per explicit owner request."""

    def __init__(
        self,
        database_path: str | Path,
        knowledge: KnowledgeStore,
        documents: DocumentStore,
        memory: MemoryStore,
    ) -> None:
        self.store = AgentRuntimeStore(database_path)
        self.knowledge = knowledge
        self.documents = documents
        self.memory = memory

    @staticmethod
    def list_agents() -> list[dict]:
        return [dict(profile) for profile in AGENT_PROFILES.values()]

    @staticmethod
    def list_tools(agent_id: str | None = None) -> list[dict]:
        if agent_id is not None and agent_id not in AGENT_PROFILES:
            raise LookupError("Agent profile was not found")
        allowed = (
            set(AGENT_PROFILES[agent_id]["tools"])
            if agent_id is not None
            else set(TOOL_CATALOG)
        )
        return [
            {"name": name, **definition}
            for name, definition in TOOL_CATALOG.items()
            if name in allowed
        ]

    def invoke(self, agent_id: str, tool_name: str, arguments: dict) -> dict:
        profile = AGENT_PROFILES.get(agent_id)
        if profile is None:
            raise LookupError("Agent profile was not found")
        if tool_name not in profile["tools"]:
            raise PermissionError("Tool is not granted to this agent profile")
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be an object")
        input_bytes = json.dumps(
            arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if len(input_bytes) > 20_000:
            raise ValueError("Agent tool arguments exceed the 20,000-byte limit")
        input_digest = hashlib.sha256(input_bytes).hexdigest()
        run_id = self.store.start_run(agent_id, tool_name, input_digest)

        heartbeat_stop = threading.Event()
        heartbeat_lost = threading.Event()

        def renew_lease() -> None:
            while not heartbeat_stop.wait(self.store.heartbeat_interval_seconds):
                try:
                    self.store.renew_run_lease(run_id)
                except (AgentRunLeaseLost, sqlite3.Error):
                    heartbeat_lost.set()
                    return

        heartbeat = threading.Thread(
            target=renew_lease,
            name=f"humanity-agent-lease-{run_id[:8]}",
            daemon=True,
        )
        heartbeat.start()

        def stop_heartbeat() -> None:
            heartbeat_stop.set()
            heartbeat.join()

        run_finished = False
        try:
            if tool_name == "knowledge.search":
                payload = SearchToolInput.model_validate(arguments)
                records = self.knowledge.list(limit=payload.limit, query=payload.query)
                result = [
                    {
                        "id": record.id,
                        "kind": record.kind,
                        "title": record.title,
                        "visibility": record.visibility,
                        "updated_at": record.updated_at.isoformat(),
                        "excerpt": record.content[:500],
                    }
                    for record in records
                ]
            elif tool_name == "documents.search":
                payload = SearchToolInput.model_validate(arguments)
                result = self.documents.search(payload.query, limit=payload.limit)
            elif tool_name == "documents.context":
                payload = ContextToolInput.model_validate(arguments)
                result = self.documents.prepare_context(
                    payload.query,
                    passage_limit=payload.passage_limit,
                    max_context_chars=payload.max_context_chars,
                )
            elif tool_name == "memory.propose":
                payload = MemoryProposalToolInput.model_validate(arguments)
                stop_heartbeat()
                if heartbeat_lost.is_set():
                    raise AgentRunLeaseLost(
                        "Agent run lease was lost before the memory proposal could be written"
                    )
                with self.store.owned_lease_transaction(run_id) as connection:
                    proposal = self.memory.create_proposal(
                        **payload.model_dump(),
                        actor=agent_id,
                        connection=connection,
                    )
                    result = {
                        "proposal_id": proposal["id"],
                        "title": proposal["title"],
                        "status": proposal["status"],
                        "requires_owner_approval": True,
                    }
                    result_bytes = json.dumps(
                        result,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    ).encode("utf-8")
                    if len(result_bytes) > 20_000:
                        raise ValueError("Agent tool result exceeds the 20,000-byte limit")
                    result_digest = hashlib.sha256(result_bytes).hexdigest()
                    self.store.finish_run(
                        run_id,
                        result_digest=result_digest,
                        connection=connection,
                    )
                run_finished = True
            else:
                raise PermissionError("Tool is not registered")
            result_bytes = json.dumps(
                result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
            if len(result_bytes) > 20_000:
                raise ValueError("Agent tool result exceeds the 20,000-byte limit")
            result_digest = hashlib.sha256(result_bytes).hexdigest()
            stop_heartbeat()
            if heartbeat_lost.is_set():
                raise AgentRunLeaseLost(
                    "Agent run lease was lost before the tool result could be committed"
                )
            if not run_finished:
                self.store.finish_run(run_id, result_digest=result_digest)
            return {
                "run_id": run_id,
                "agent_id": agent_id,
                "tool_name": tool_name,
                "result": result,
            }
        except AgentRunLeaseLost:
            stop_heartbeat()
            raise
        except Exception as exc:
            stop_heartbeat()
            try:
                self.store.finish_run(run_id, error_code=type(exc).__name__)
            except AgentRunLeaseLost as lease_error:
                raise lease_error from exc
            raise
        finally:
            stop_heartbeat()



__all__ = [
    "AGENT_PROFILES",
    "TOOL_CATALOG",
    "AgentRunLeaseLost",
    "AgentRuntime",
    "AgentRuntimeStore",
]
