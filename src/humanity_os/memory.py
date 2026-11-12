"""Explicit owner-approved durable memory lifecycle."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class MemoryStore:
    """Proposals never become memory without a separate approval operation."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memory_proposals (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    source_document_id TEXT,
                    source_chunk_id TEXT,
                    status TEXT NOT NULL CHECK(status IN ('pending_review', 'approved', 'rejected')),
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    approved_memory_id TEXT
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL UNIQUE REFERENCES memory_proposals(id),
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    rationale TEXT NOT NULL,
                    source_document_id TEXT,
                    source_chunk_id TEXT,
                    status TEXT NOT NULL CHECK(status IN ('active', 'archived')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memory_events (
                    id TEXT PRIMARY KEY,
                    proposal_id TEXT REFERENCES memory_proposals(id),
                    memory_id TEXT REFERENCES memory_items(id),
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    details TEXT NOT NULL,
                    CHECK(proposal_id IS NOT NULL OR memory_id IS NOT NULL)
                )"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS memory_events_no_update
                   BEFORE UPDATE ON memory_events
                   BEGIN SELECT RAISE(ABORT, 'memory events are append-only'); END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS memory_events_no_delete
                   BEFORE DELETE ON memory_events
                   BEGIN SELECT RAISE(ABORT, 'memory events are append-only'); END"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_proposals_status "
                "ON memory_proposals(status, created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_items_status "
                "ON memory_items(status, updated_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_events_time "
                "ON memory_events(occurred_at DESC, id DESC)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _event(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        actor: str,
        details: dict,
        proposal_id: str | None = None,
        memory_id: str | None = None,
        occurred_at: str,
    ) -> None:
        connection.execute(
            """INSERT INTO memory_events(
                id, proposal_id, memory_id, event_type, actor, occurred_at, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid4()), proposal_id, memory_id, event_type, actor,
                occurred_at, json.dumps(details, ensure_ascii=False, sort_keys=True),
            ),
        )

    def create_proposal(
        self,
        *,
        title: str,
        content: str,
        rationale: str,
        source_document_id: str | None = None,
        source_chunk_id: str | None = None,
    ) -> dict:
        if (source_document_id is None) != (source_chunk_id is None):
            raise ValueError("Document and chunk source references must be supplied together")
        proposal_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            if source_document_id is not None:
                source = connection.execute(
                    """SELECT 1 FROM document_chunks
                       WHERE id = ? AND document_id = ?""",
                    (source_chunk_id, source_document_id),
                ).fetchone()
                if source is None:
                    raise LookupError("Source document chunk was not found")
            connection.execute(
                """INSERT INTO memory_proposals(
                    id, title, content, rationale, source_document_id,
                    source_chunk_id, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending_review', ?)""",
                (
                    proposal_id, title, content, rationale, source_document_id,
                    source_chunk_id, created_at,
                ),
            )
            self._event(
                connection,
                event_type="proposal_created",
                actor="owner",
                details={"status": "pending_review"},
                proposal_id=proposal_id,
                occurred_at=created_at,
            )
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM memory_proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_proposals(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("Proposal limit must be between 1 and 100")
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM memory_proposals ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM memory_proposals WHERE status = ?
                       ORDER BY created_at DESC, id DESC LIMIT ?""",
                    (status, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def approve(self, proposal_id: str) -> dict:
        approved_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            proposal = connection.execute(
                "SELECT * FROM memory_proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
            if proposal is None:
                raise LookupError("Memory proposal was not found")
            if proposal["status"] != "pending_review":
                raise ValueError("Only pending proposals can be approved")
            content_hash = hashlib.sha256(proposal["content"].encode("utf-8")).hexdigest()
            memory_id = str(uuid4())
            try:
                connection.execute(
                    """INSERT INTO memory_items(
                        id, proposal_id, title, content, content_hash, rationale,
                        source_document_id, source_chunk_id, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
                    (
                        memory_id, proposal_id, proposal["title"], proposal["content"],
                        content_hash, proposal["rationale"], proposal["source_document_id"],
                        proposal["source_chunk_id"], approved_at, approved_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("Identical content already exists in durable memory") from exc
            connection.execute(
                """UPDATE memory_proposals SET status = 'approved',
                   reviewed_at = ?, approved_memory_id = ? WHERE id = ?""",
                (approved_at, memory_id, proposal_id),
            )
            self._event(
                connection,
                event_type="proposal_approved",
                actor="owner",
                details={"status": "active"},
                proposal_id=proposal_id,
                memory_id=memory_id,
                occurred_at=approved_at,
            )
        return self.get_memory(memory_id)

    def reject(self, proposal_id: str) -> dict:
        rejected_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            proposal = connection.execute(
                "SELECT status FROM memory_proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
            if proposal is None:
                raise LookupError("Memory proposal was not found")
            if proposal["status"] != "pending_review":
                raise ValueError("Only pending proposals can be rejected")
            connection.execute(
                """UPDATE memory_proposals SET status = 'rejected', reviewed_at = ?
                   WHERE id = ?""",
                (rejected_at, proposal_id),
            )
            self._event(
                connection,
                event_type="proposal_rejected",
                actor="owner",
                details={"status": "rejected"},
                proposal_id=proposal_id,
                occurred_at=rejected_at,
            )
        return self.get_proposal(proposal_id)

    def get_memory(self, memory_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM memory_items WHERE id = ?", (memory_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_memories(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("Memory limit must be between 1 and 100")
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM memory_items ORDER BY updated_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM memory_items WHERE status = ?
                       ORDER BY updated_at DESC, id DESC LIMIT ?""",
                    (status, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    def set_archived(self, memory_id: str, archived: bool) -> dict | None:
        occurred_at = datetime.now(UTC).isoformat()
        target = "archived" if archived else "active"
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM memory_items WHERE id = ?", (memory_id,)
            ).fetchone()
            if row is None:
                return None
            if row["status"] == target:
                raise ValueError(f"Memory is already {target}")
            connection.execute(
                "UPDATE memory_items SET status = ?, updated_at = ? WHERE id = ?",
                (target, occurred_at, memory_id),
            )
            self._event(
                connection,
                event_type="memory_archived" if archived else "memory_restored",
                actor="owner",
                details={"status": target},
                memory_id=memory_id,
                occurred_at=occurred_at,
            )
        return self.get_memory(memory_id)

    def list_events(self, proposal_id: str | None = None, memory_id: str | None = None) -> list[dict]:
        if proposal_id is not None and memory_id is not None:
            raise ValueError("Filter by proposal or memory, not both")
        with self._connect() as connection:
            if proposal_id is not None:
                rows = connection.execute(
                    """SELECT * FROM memory_events WHERE proposal_id = ?
                       ORDER BY occurred_at, id""",
                    (proposal_id,),
                ).fetchall()
            elif memory_id is not None:
                rows = connection.execute(
                    """SELECT * FROM memory_events WHERE memory_id = ?
                       ORDER BY occurred_at, id""",
                    (memory_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM memory_events ORDER BY occurred_at DESC, id DESC LIMIT 100"
                ).fetchall()
        return [dict(row) for row in rows]
