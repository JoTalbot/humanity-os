"""Append-only claim graph persistence for the local HUMANITY OS prototype."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from humanity_os.models import ClaimNode, ClaimRelation


class ClaimGraphStore:
    """Persists atomic claims and typed relations without inferring truth."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    knowledge_id TEXT NOT NULL REFERENCES knowledge(id),
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_claims_knowledge_time "
                "ON claims(knowledge_id, created_at DESC, id DESC)"
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS claim_relations (
                    id TEXT PRIMARY KEY,
                    source_claim_id TEXT NOT NULL REFERENCES claims(id),
                    target_claim_id TEXT NOT NULL REFERENCES claims(id),
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(source_claim_id, target_claim_id, relation),
                    CHECK(source_claim_id <> target_claim_id)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_claim_relations_source "
                "ON claim_relations(source_claim_id, created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_claim_relations_target "
                "ON claim_relations(target_claim_id, created_at DESC)"
            )
            for table in ("claims", "claim_relations"):
                connection.execute(
                    f"""CREATE TRIGGER IF NOT EXISTS {table}_no_update
                        BEFORE UPDATE ON {table}
                        BEGIN SELECT RAISE(ABORT, '{table} are append-only'); END"""
                )
                connection.execute(
                    f"""CREATE TRIGGER IF NOT EXISTS {table}_no_delete
                        BEFORE DELETE ON {table}
                        BEGIN SELECT RAISE(ABORT, '{table} are append-only'); END"""
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_claim(self, claim: ClaimNode) -> ClaimNode:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO claims(id, knowledge_id, created_at, payload) VALUES (?, ?, ?, ?)",
                (claim.id, claim.knowledge_id, claim.created_at.isoformat(), claim.model_dump_json()),
            )
        return claim

    def get_claim(self, claim_id: str) -> ClaimNode | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM claims WHERE id = ?", (claim_id,)
            ).fetchone()
        return ClaimNode.model_validate_json(row["payload"]) if row else None

    def list_claims(self, knowledge_id: str | None = None, limit: int = 100) -> list[ClaimNode]:
        if not 1 <= limit <= 100:
            raise ValueError("Claim limit must be between 1 and 100")
        sql = "SELECT payload FROM claims"
        params: list[object] = []
        if knowledge_id is not None:
            sql += " WHERE knowledge_id = ?"
            params.append(knowledge_id)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [ClaimNode.model_validate_json(row["payload"]) for row in rows]

    def create_relation(self, relation: ClaimRelation) -> ClaimRelation:
        source_id, target_id = relation.source_claim_id, relation.target_claim_id
        if relation.relation == "contradicts" and target_id < source_id:
            relation = relation.model_copy(
                update={"source_claim_id": target_id, "target_claim_id": source_id}
            )
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO claim_relations(
                    id, source_claim_id, target_claim_id, relation, created_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    relation.id,
                    relation.source_claim_id,
                    relation.target_claim_id,
                    relation.relation,
                    relation.created_at.isoformat(),
                    relation.model_dump_json(),
                ),
            )
        return relation

    def list_relations(self, claim_id: str | None = None, limit: int = 100) -> list[ClaimRelation]:
        if not 1 <= limit <= 100:
            raise ValueError("Claim relation limit must be between 1 and 100")
        sql = "SELECT payload FROM claim_relations"
        params: list[object] = []
        if claim_id is not None:
            sql += " WHERE source_claim_id = ? OR target_claim_id = ?"
            params.extend((claim_id, claim_id))
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [ClaimRelation.model_validate_json(row["payload"]) for row in rows]
