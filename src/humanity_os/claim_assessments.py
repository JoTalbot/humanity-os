"""Append-only human-reviewed epistemic assessments for claim nodes."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from humanity_os.models import ClaimAssessment


class ClaimAssessmentStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS claim_assessments (
                    id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL REFERENCES claims(id),
                    assessed_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_claim_assessments_claim_time "
                "ON claim_assessments(claim_id, assessed_at DESC, id DESC)"
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS claim_assessments_no_update
                   BEFORE UPDATE ON claim_assessments
                   BEGIN SELECT RAISE(ABORT, 'claim assessments are append-only'); END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS claim_assessments_no_delete
                   BEFORE DELETE ON claim_assessments
                   BEGIN SELECT RAISE(ABORT, 'claim assessments are append-only'); END"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create(self, assessment: ClaimAssessment) -> ClaimAssessment:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO claim_assessments(id, claim_id, assessed_at, payload) "
                "VALUES (?, ?, ?, ?)",
                (
                    assessment.id,
                    assessment.claim_id,
                    assessment.assessed_at.isoformat(),
                    assessment.model_dump_json(),
                ),
            )
        return assessment

    def list_for_claim(self, claim_id: str, limit: int = 100) -> list[ClaimAssessment]:
        if not 1 <= limit <= 100:
            raise ValueError("Assessment limit must be between 1 and 100")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM claim_assessments WHERE claim_id = ? "
                "ORDER BY assessed_at DESC, id DESC LIMIT ?",
                (claim_id, limit),
            ).fetchall()
        return [ClaimAssessment.model_validate_json(row["payload"]) for row in rows]

    def latest_for_claims(self, claim_ids: list[str]) -> list[ClaimAssessment]:
        if not claim_ids:
            return []
        placeholders = ",".join("?" for _ in claim_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT payload FROM (
                        SELECT payload, claim_id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY claim_id
                                   ORDER BY assessed_at DESC, id DESC
                               ) AS position
                        FROM claim_assessments
                        WHERE claim_id IN ({placeholders})
                    ) WHERE position = 1
                    ORDER BY claim_id""",
                claim_ids,
            ).fetchall()
        return [ClaimAssessment.model_validate_json(row["payload"]) for row in rows]

    @staticmethod
    def verify_rows(rows: list[tuple[str]]) -> None:
        for (payload,) in rows:
            ClaimAssessment.model_validate_json(payload)
