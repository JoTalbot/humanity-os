"""Single-owner password and opaque-session storage for the local prototype."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

SESSION_TTL = timedelta(hours=12)
_password_hasher = PasswordHasher()


class AuthStore:
    def __init__(self, database_path: str | Path) -> None:
        raw = str(database_path)
        self.database_path = str(Path(raw).expanduser()) if raw != ":memory:" else raw
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS owner_identity (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    password_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    csrf_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at)"
            )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def has_owner(self) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 FROM owner_identity WHERE id = 1").fetchone()
        return row is not None

    def set_owner_password(self, password: str) -> None:
        if len(password) < 12:
            raise ValueError("Owner password must contain at least 12 characters")
        password_hash = _password_hasher.hash(password)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO owner_identity(id, password_hash, updated_at)
                   VALUES (1, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     password_hash = excluded.password_hash,
                     updated_at = excluded.updated_at""",
                (password_hash, datetime.now(UTC).isoformat()),
            )
            connection.execute("DELETE FROM auth_sessions")

    def verify_owner_password(self, password: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM owner_identity WHERE id = 1"
            ).fetchone()
        if row is None:
            return False
        try:
            return _password_hasher.verify(row["password_hash"], password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def create_session(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO auth_sessions(token_hash, csrf_hash, created_at, expires_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    self._digest(token),
                    self._digest(csrf),
                    now.isoformat(),
                    (now + SESSION_TTL).isoformat(),
                ),
            )
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now.isoformat(),))
        return token, csrf

    def validate_session(self, token: str) -> bool:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT expires_at FROM auth_sessions WHERE token_hash = ?",
                (self._digest(token),),
            ).fetchone()
            if row is None:
                return False
            if row["expires_at"] <= now:
                connection.execute(
                    "DELETE FROM auth_sessions WHERE token_hash = ?", (self._digest(token),)
                )
                return False
        return True

    def validate_csrf(self, token: str, csrf: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT csrf_hash FROM auth_sessions WHERE token_hash = ?",
                (self._digest(token),),
            ).fetchone()
        return row is not None and secrets.compare_digest(
            row["csrf_hash"], self._digest(csrf)
        )

    def revoke_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?", (self._digest(token),)
            )

    def revoke_all_sessions(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM auth_sessions")
