"""SQLite persistence for the local single-user prototype."""
from __future__ import annotations
import base64
import binascii
import sqlite3
from pathlib import Path

from humanity_os.models import KnowledgeRecord


class KnowledgeStore:
    def __init__(self, database_path: str | Path) -> None:
        raw_path = str(database_path)
        self.database_path = str(Path(raw_path).expanduser()) if raw_path != ":memory:" else raw_path
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY, visibility TEXT NOT NULL,
                    created_at TEXT NOT NULL, payload TEXT NOT NULL)"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_created_id "
                "ON knowledge(created_at DESC, id DESC)"
            )

    @staticmethod
    def encode_cursor(record: KnowledgeRecord) -> str:
        raw = f"{record.created_at.isoformat()}|{record.id}".encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def decode_cursor(cursor: str) -> tuple[str, str]:
        try:
            if not cursor or len(cursor) > 512:
                raise ValueError
            padded = cursor + "=" * (-len(cursor) % 4)
            raw = base64.b64decode(padded, altchars=b"-_", validate=True).decode()
            created_at, record_id = raw.split("|", 1)
            if not created_at or not record_id:
                raise ValueError
            return created_at, record_id
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise ValueError("Invalid pagination cursor") from exc

    def create(self, record: KnowledgeRecord) -> KnowledgeRecord:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO knowledge(id, visibility, created_at, payload) VALUES (?, ?, ?, ?)",
                (record.id, record.visibility, record.created_at.isoformat(), record.model_dump_json()),
            )
        return record

    def get(self, record_id: str) -> KnowledgeRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM knowledge WHERE id = ?", (record_id,)
            ).fetchone()
        return KnowledgeRecord.model_validate_json(row["payload"]) if row else None

    def list(
        self, limit: int = 50, cursor: str | None = None, query: str | None = None
    ) -> list[KnowledgeRecord]:
        sql = "SELECT payload FROM knowledge"
        clauses: list[str] = []
        params: list[object] = []
        if query:
            escaped = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            clauses.append("(payload LIKE ? ESCAPE '!')")
            params.append(f"%{escaped}%")
        if cursor:
            created_at, record_id = self.decode_cursor(cursor)
            clauses.append("(created_at < ? OR (created_at = ? AND id < ?))")
            params.extend((created_at, created_at, record_id))
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [KnowledgeRecord.model_validate_json(row["payload"]) for row in rows]

    def update(self, record: KnowledgeRecord) -> KnowledgeRecord | None:
        with self._connect() as connection:
            result = connection.execute(
                "UPDATE knowledge SET visibility = ?, payload = ? WHERE id = ?",
                (record.visibility, record.model_dump_json(), record.id),
            )
        return record if result.rowcount else None

    def delete(self, record_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM knowledge WHERE id = ?", (record_id,))
        return result.rowcount > 0

    def export_all(self) -> list[KnowledgeRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM knowledge ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [KnowledgeRecord.model_validate_json(row["payload"]) for row in rows]
