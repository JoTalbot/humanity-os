"""Local, source-preserving text and Markdown document ingestion."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

MAX_DOCUMENT_CHARS = 1_000_000
CHUNK_SIZE = 1_200
CHUNK_OVERLAP = 150
ALLOWED_SUFFIXES = {".txt", ".md", ".markdown"}


class DocumentStore:
    """Persist bounded local documents and deterministic, attributable chunks."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    character_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    content TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    start_offset INTEGER NOT NULL,
                    end_offset INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    UNIQUE(document_id, ordinal)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_document_chunks_document "
                "ON document_chunks(document_id, ordinal)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _normalize(filename: str, content: str) -> tuple[str, str, str]:
        safe_name = Path(filename.replace("\\", "/")).name.strip()
        suffix = Path(safe_name).suffix.lower()
        if not safe_name or suffix not in ALLOWED_SUFFIXES:
            raise ValueError("Only .txt, .md, and .markdown documents are supported")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Document content must be non-empty UTF-8 text")
        if "\x00" in content:
            raise ValueError("Document content cannot contain NUL characters")
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        if len(normalized) > MAX_DOCUMENT_CHARS:
            raise ValueError("Document exceeds the 1,000,000 character limit")
        media_type = "text/markdown" if suffix in {".md", ".markdown"} else "text/plain"
        return safe_name, normalized, media_type

    @staticmethod
    def _chunk_ranges(content: str) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        start = 0
        length = len(content)
        while start < length:
            end = min(start + CHUNK_SIZE, length)
            if end < length:
                boundary = content.rfind("\n", start + CHUNK_SIZE // 2, end)
                if boundary > start:
                    end = boundary + 1
            ranges.append((start, end))
            if end >= length:
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
        return ranges

    def create(self, filename: str, content: str) -> dict:
        safe_name, normalized, media_type = self._normalize(filename, content)
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        document_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        ranges = self._chunk_ranges(normalized)
        chunks = []
        for ordinal, (start, end) in enumerate(ranges):
            chunk_text = normalized[start:end]
            chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            chunk_id = hashlib.sha256(
                f"{document_id}:{ordinal}:{start}:{end}:{chunk_hash}".encode()
            ).hexdigest()
            chunks.append(
                {
                    "id": chunk_id,
                    "document_id": document_id,
                    "ordinal": ordinal,
                    "start_offset": start,
                    "end_offset": end,
                    "content_hash": chunk_hash,
                    "content": chunk_text,
                }
            )
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO documents(
                        id, filename, media_type, content_hash, character_count,
                        chunk_count, status, created_at, content
                    ) VALUES (?, ?, ?, ?, ?, ?, 'ready', ?, ?)""",
                    (
                        document_id, safe_name, media_type, content_hash, len(normalized),
                        len(chunks), created_at, normalized,
                    ),
                )
                connection.executemany(
                    """INSERT INTO document_chunks(
                        id, document_id, ordinal, start_offset, end_offset,
                        content_hash, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    [
                        (
                            item["id"], item["document_id"], item["ordinal"],
                            item["start_offset"], item["end_offset"],
                            item["content_hash"], item["content"],
                        )
                        for item in chunks
                    ],
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("A document with identical content already exists") from exc
        return self.get(document_id)

    def get(self, document_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT id, filename, media_type, content_hash, character_count,
                          chunk_count, status, created_at
                   FROM documents WHERE id = ?""",
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            chunks = connection.execute(
                """SELECT id, ordinal, start_offset, end_offset, content_hash, content
                   FROM document_chunks WHERE document_id = ? ORDER BY ordinal""",
                (document_id,),
            ).fetchall()
        result = dict(row)
        result["chunks"] = [dict(item) for item in chunks]
        return result

    def verify_source(self, source: dict) -> bool:
        """Verify a context source against the current stored document and chunk."""
        with self._connect() as connection:
            row = connection.execute(
                """SELECT d.id AS document_id, d.filename, d.media_type,
                          d.content_hash AS document_hash, d.content AS document_content,
                          c.id AS chunk_id, c.ordinal, c.start_offset, c.end_offset,
                          c.content_hash AS chunk_hash, c.content AS excerpt
                   FROM documents d
                   JOIN document_chunks c ON c.document_id = d.id
                   WHERE d.id = ? AND c.id = ?""",
                (source.get("document_id"), source.get("chunk_id")),
            ).fetchone()
        if row is None:
            return False
        item = dict(row)
        start = item["start_offset"]
        end = item["end_offset"]
        if (
            source.get("filename") != item["filename"]
            or source.get("media_type") != item["media_type"]
            or source.get("document_hash") != item["document_hash"]
            or source.get("chunk_hash") != item["chunk_hash"]
            or source.get("start_offset") != start
            or source.get("end_offset") != end
            or source.get("ordinal") != item["ordinal"]
            or source.get("excerpt") != item["excerpt"]
            or hashlib.sha256(item["document_content"].encode("utf-8")).hexdigest() != item["document_hash"]
            or hashlib.sha256(item["excerpt"].encode("utf-8")).hexdigest() != item["chunk_hash"]
            or item["document_content"][start:end] != item["excerpt"]
        ):
            return False
        expected_chunk_id = hashlib.sha256(
            f"{item['document_id']}:{item['ordinal']}:{start}:{end}:{item['chunk_hash']}".encode()
        ).hexdigest()
        expected_citation_id = "src-" + hashlib.sha256(
            ":".join(str(source[key]) for key in (
                "document_id", "chunk_id", "document_hash", "chunk_hash",
                "start_offset", "end_offset",
            )).encode("utf-8")
        ).hexdigest()[:24]
        return (
            source.get("chunk_id") == item["chunk_id"]
            and source.get("citation_id") == expected_citation_id
            and expected_chunk_id == item["chunk_id"]
        )
    def list(self, limit: int = 50) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("Document limit must be between 1 and 100")
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT id, filename, media_type, content_hash, character_count,
                          chunk_count, status, created_at
                   FROM documents ORDER BY created_at DESC, id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        if not 1 <= limit <= 50:
            raise ValueError("Search limit must be between 1 and 50")
        terms = [term for term in re.findall(r"[\w-]{2,}", query.casefold())][:12]
        if not terms:
            raise ValueError("Search query must contain at least one word")
        results = []
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT d.id AS document_id, d.filename, d.media_type,
                          d.content_hash AS document_hash, d.created_at, c.id AS chunk_id, c.ordinal, c.start_offset,
                          c.end_offset, c.content_hash AS chunk_hash, c.content AS excerpt
                   FROM document_chunks c
                   JOIN documents d ON d.id = c.document_id
                   ORDER BY d.created_at DESC, c.ordinal ASC"""
            )
            for row in rows:
                item = dict(row)
                normalized_excerpt = item["excerpt"].casefold()
                if all(term in normalized_excerpt for term in terms):
                    item.pop("created_at")
                    results.append(item)
                    if len(results) == limit:
                        break
        return results
