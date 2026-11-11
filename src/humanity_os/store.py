"""SQLite persistence for the local single-user prototype."""
import base64
import sqlite3
from pathlib import Path
from humanity_os.models import KnowledgeRecord

class KnowledgeStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY, visibility TEXT NOT NULL,
                created_at TEXT NOT NULL, payload TEXT NOT NULL)""")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_created_id ON knowledge(created_at DESC, id DESC)")

    @staticmethod
    def encode_cursor(record: KnowledgeRecord) -> str:
        raw = f"{record.created_at.isoformat()}|{record.id}".encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    @staticmethod
    def decode_cursor(cursor: str) -> tuple[str, str]:
        try:
            raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
            created_at, record_id = raw.split("|", 1)
            return created_at, record_id
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid pagination cursor") from exc

    def create(self, record: KnowledgeRecord) -> KnowledgeRecord:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO knowledge(id, visibility, created_at, payload) VALUES (?, ?, ?, ?)",
                (record.id, record.visibility, record.created_at.isoformat(), record.model_dump_json()))
        return record

    def get(self, record_id: str) -> KnowledgeRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM knowledge WHERE id = ?", (record_id,)).fetchone()
        return KnowledgeRecord.model_validate_json(row["payload"]) if row else None

    def list(self, limit: int = 50, cursor: str | None = None) -> list[KnowledgeRecord]:
        with self._connect() as connection:
            if cursor:
                created_at, record_id = self.decode_cursor(cursor)
                rows = connection.execute(
                    """SELECT payload FROM knowledge
                    WHERE created_at < ? OR (created_at = ? AND id < ?)
                    ORDER BY created_at DESC, id DESC LIMIT ?""",
                    (created_at, created_at, record_id, limit)).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM knowledge ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,)).fetchall()
        return [KnowledgeRecord.model_validate_json(row["payload"]) for row in rows]

    def delete(self, record_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM knowledge WHERE id = ?", (record_id,))
        return result.rowcount > 0
