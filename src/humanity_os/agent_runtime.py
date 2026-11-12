"""Constrained local agent runtime with explicit capability allowlists."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
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


class AgentRuntimeStore:
    """Persist minimal run metadata and append-only invocation events."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
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
                    error_code TEXT
                )"""
            )
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
                "CREATE INDEX IF NOT EXISTS idx_agent_events_run "
                "ON agent_events(run_id, occurred_at, id)"
            )
            interrupted = connection.execute(
                "SELECT id FROM agent_runs WHERE status = 'running'"
            ).fetchall()
            for row in interrupted:
                finished_at = datetime.now(UTC).isoformat()
                connection.execute(
                    """UPDATE agent_runs SET status = 'failed', finished_at = ?,
                       error_code = 'interrupted' WHERE id = ?""",
                    (finished_at, row["id"]),
                )
                self._append_event(
                    connection,
                    row["id"],
                    "tool_invocation_failed",
                    finished_at,
                    {"status": "failed", "error_code": "interrupted"},
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

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

    def start_run(self, agent_id: str, tool_name: str, input_digest: str) -> str:
        run_id = str(uuid4())
        started_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO agent_runs(
                    id, agent_id, tool_name, status, started_at, input_digest
                ) VALUES (?, ?, ?, 'running', ?, ?)""",
                (run_id, agent_id, tool_name, started_at, input_digest),
            )
            self._append_event(
                connection,
                run_id,
                "tool_invocation_started",
                started_at,
                {"agent_id": agent_id, "tool_name": tool_name},
            )
        return run_id

    def finish_run(
        self,
        run_id: str,
        *,
        result_digest: str | None = None,
        error_code: str | None = None,
    ) -> None:
        finished_at = datetime.now(UTC).isoformat()
        status = "failed" if error_code else "completed"
        with self._connect() as connection:
            connection.execute(
                """UPDATE agent_runs SET status = ?, finished_at = ?,
                   result_digest = ?, error_code = ? WHERE id = ?""",
                (status, finished_at, result_digest, error_code, run_id),
            )
            self._append_event(
                connection,
                run_id,
                "tool_invocation_failed" if error_code else "tool_invocation_completed",
                finished_at,
                {"status": status, "error_code": error_code},
            )

    def list_runs(self, limit: int = 50) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("Agent run limit must be between 1 and 100")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM agent_runs ORDER BY started_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_events(self, run_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if run_id is None:
                rows = connection.execute(
                    "SELECT * FROM agent_events ORDER BY occurred_at DESC, id DESC LIMIT 100"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM agent_events WHERE run_id = ? ORDER BY occurred_at, id",
                    (run_id,),
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
            raise ValueError("Tool arguments must be an object")
        input_bytes = json.dumps(
            arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if len(input_bytes) > 20_000:
            raise ValueError("Agent tool arguments exceed the 20,000-byte limit")
        input_digest = hashlib.sha256(input_bytes).hexdigest()
        run_id = self.store.start_run(agent_id, tool_name, input_digest)
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
                proposal = self.memory.create_proposal(**payload.model_dump())
                result = {
                    "proposal_id": proposal["id"],
                    "title": proposal["title"],
                    "status": proposal["status"],
                    "requires_owner_approval": True,
                }
            else:
                raise PermissionError("Tool is not registered")
            result_bytes = json.dumps(
                result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
            if len(result_bytes) > 20_000:
                raise ValueError("Agent tool result exceeds the 20,000-byte limit")
            result_digest = hashlib.sha256(result_bytes).hexdigest()
            self.store.finish_run(run_id, result_digest=result_digest)
            return {"run_id": run_id, "agent_id": agent_id, "tool_name": tool_name, "result": result}
        except Exception as exc:
            self.store.finish_run(run_id, error_code=type(exc).__name__)
            raise


__all__ = [
    "AGENT_PROFILES",
    "TOOL_CATALOG",
    "AgentRuntime",
    "AgentRuntimeStore",
]
