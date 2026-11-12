"""SQLite persistence for the local single-user prototype."""
from __future__ import annotations

import base64
import binascii
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from contextlib import closing
from pathlib import Path

from humanity_os.models import KnowledgeConflict, KnowledgeRecord


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
            connection.execute(
                """CREATE TABLE IF NOT EXISTS knowledge_conflicts (
                    id TEXT PRIMARY KEY,
                    record_a_id TEXT NOT NULL REFERENCES knowledge(id),
                    record_b_id TEXT NOT NULL REFERENCES knowledge(id),
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    UNIQUE(record_a_id, record_b_id),
                    CHECK(record_a_id < record_b_id)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_conflicts_status "
                "ON knowledge_conflicts(status, created_at DESC)"
            )

    def backup(self, destination: str | Path) -> Path:
        """Create a consistent SQLite snapshot without overwriting an existing file."""
        target_path = Path(destination).expanduser()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if (
            self.database_path != ":memory:"
            and target_path.resolve() == Path(self.database_path).resolve()
        ):
            raise ValueError("Backup destination must differ from the active database")

        # O_EXCL prevents clobbering existing files and symlinks; 0600 protects personal data.
        descriptor = os.open(target_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            with closing(self._connect()) as source, closing(
                sqlite3.connect(str(target_path))
            ) as target:
                source.backup(target)
                result = target.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok":
                    raise sqlite3.DatabaseError(f"Backup integrity check failed: {result}")
                tables = {
                    row[0]
                    for row in target.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                if "knowledge" not in tables:
                    raise sqlite3.DatabaseError("Backup is missing the knowledge table")
            return target_path
        except Exception:
            target_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def verify_backup(backup_path: str | Path) -> int:
        """Verify SQLite integrity and every stored record; return record count."""
        path = Path(backup_path).expanduser()
        uri = f"{path.resolve().as_uri()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise sqlite3.DatabaseError(f"Backup integrity check failed: {result}")
            rows = connection.execute("SELECT payload FROM knowledge").fetchall()
            conflict_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_conflicts'"
            ).fetchone()
            conflict_rows = (
                connection.execute("SELECT payload FROM knowledge_conflicts").fetchall()
                if conflict_table
                else []
            )
        for row in rows:
            KnowledgeRecord.model_validate_json(row[0])
        for row in conflict_rows:
            KnowledgeConflict.model_validate_json(row[0])
        return len(rows)


    def restore(self, backup_path: str | Path, safety_backup_path: str | Path) -> int:
        """Restore a verified snapshot after making a separate pre-restore backup.

        The caller must stop the application before invoking this operation.
        The active database is replaced atomically only after staging and validation.
        """
        if self.database_path == ":memory:":
            raise ValueError("Restore requires a file-backed database")
        database = Path(self.database_path)
        if database.is_symlink():
            raise ValueError("Refusing to replace a database symlink")
        source = Path(backup_path).expanduser()
        safety = Path(safety_backup_path).expanduser()
        if source.resolve() == database.resolve():
            raise ValueError("Restore source must differ from the active database")
        if safety.resolve() in {database.resolve(), source.resolve()}:
            raise ValueError("Safety backup must be a separate file")
        record_count = self.verify_backup(source)

        # Preserve the current state before preparing any replacement.
        self.backup(safety)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{database.name}.restore-",
            suffix=".sqlite3",
            dir=str(database.parent),
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            source_uri = f"{source.resolve().as_uri()}?mode=ro"
            with closing(sqlite3.connect(source_uri, uri=True)) as source_connection, closing(
                sqlite3.connect(str(temporary))
            ) as staged_connection:
                source_connection.backup(staged_connection)
            staged_count = self.verify_backup(temporary)
            if staged_count != record_count:
                raise sqlite3.DatabaseError("Staged restore record count changed")
            os.replace(temporary, database)
            return record_count
        finally:
            temporary.unlink(missing_ok=True)

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

    def create_conflict(self, conflict: KnowledgeConflict) -> KnowledgeConflict:
        if conflict.record_a_id >= conflict.record_b_id:
            raise ValueError("Conflict record IDs must be stored in canonical order")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO knowledge_conflicts(
                       id, record_a_id, record_b_id, status, created_at, payload
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    conflict.id,
                    conflict.record_a_id,
                    conflict.record_b_id,
                    conflict.status,
                    conflict.created_at.isoformat(),
                    conflict.model_dump_json(),
                ),
            )
        return conflict

    def get_conflict(self, conflict_id: str) -> KnowledgeConflict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM knowledge_conflicts WHERE id = ?", (conflict_id,)
            ).fetchone()
        return KnowledgeConflict.model_validate_json(row["payload"]) if row else None

    def list_conflicts(
        self, status: str | None = None, limit: int = 50
    ) -> list[KnowledgeConflict]:
        if not 1 <= limit <= 100:
            raise ValueError("Conflict limit must be between 1 and 100")
        sql = "SELECT payload FROM knowledge_conflicts"
        params: list[object] = []
        if status is not None:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [KnowledgeConflict.model_validate_json(row["payload"]) for row in rows]

    def decide_conflict(
        self, conflict_id: str, status: str, resolution_note: str
    ) -> KnowledgeConflict | None:
        existing = self.get_conflict(conflict_id)
        if existing is None or existing.status != "pending_review":
            return None
        updated = existing.model_copy(
            update={
                "status": status,
                "resolution_note": resolution_note,
                "updated_at": datetime.now(UTC),
            }
        )
        with self._connect() as connection:
            result = connection.execute(
                """UPDATE knowledge_conflicts
                   SET status = ?, payload = ? WHERE id = ? AND status = 'pending_review'""",
                (updated.status, updated.model_dump_json(), conflict_id),
            )
        return updated if result.rowcount else None

    def export_all(self) -> list[KnowledgeRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM knowledge ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [KnowledgeRecord.model_validate_json(row["payload"]) for row in rows]
