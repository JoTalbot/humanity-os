"""Append-only persistence for human-reviewed evidence assessments."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from humanity_os.models import EvidenceAssessment


class EvidenceAssessmentStore:
    """Stores assessment events separately from immutable source declarations."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS evidence_assessments (
                    id TEXT PRIMARY KEY,
                    knowledge_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    assessed_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE INDEX IF NOT EXISTS idx_evidence_assessments_source_time
                   ON evidence_assessments(knowledge_id, source_id, assessed_at DESC, id DESC)"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS evidence_assessments_no_update
                   BEFORE UPDATE ON evidence_assessments
                   BEGIN SELECT RAISE(ABORT, 'evidence assessments are append-only'); END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS evidence_assessments_no_delete
                   BEFORE DELETE ON evidence_assessments
                   BEGIN SELECT RAISE(ABORT, 'evidence assessments are append-only'); END"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create(self, assessment: EvidenceAssessment) -> EvidenceAssessment:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO evidence_assessments(
                       id, knowledge_id, source_id, assessed_at, payload
                   ) VALUES (?, ?, ?, ?, ?)""",
                (
                    assessment.id,
                    assessment.knowledge_id,
                    assessment.source_id,
                    assessment.assessed_at.isoformat(),
                    assessment.model_dump_json(),
                ),
            )
        return assessment

    def list_for_knowledge(
        self, knowledge_id: str, limit: int = 100
    ) -> list[EvidenceAssessment]:
        if not 1 <= limit <= 100:
            raise ValueError("Assessment limit must be between 1 and 100")
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT payload FROM evidence_assessments
                   WHERE knowledge_id = ?
                   ORDER BY assessed_at DESC, id DESC LIMIT ?""",
                (knowledge_id, limit),
            ).fetchall()
        return [EvidenceAssessment.model_validate_json(row["payload"]) for row in rows]

    @staticmethod
    def verify_rows(rows: list[tuple[str]]) -> None:
        for (payload,) in rows:
            EvidenceAssessment.model_validate_json(payload)
