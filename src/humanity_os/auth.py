"""Single-owner password and opaque-session storage for the local prototype."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

SESSION_TTL = timedelta(hours=12)
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_BLOCK = timedelta(minutes=15)
LOGIN_MAX_ATTEMPTS = 5
_password_hasher = PasswordHasher(type=Type.ID)


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
            connection.execute(
                """CREATE TABLE IF NOT EXISTS auth_login_limits (
                    bucket_key TEXT PRIMARY KEY,
                    window_started_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    blocked_until TEXT
                )"""
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

    def consume_login_attempts(self, bucket_keys: tuple[str, ...]) -> int:
        """Atomically reserve an attempt across all login buckets.

        The transaction prevents concurrent requests from racing past the threshold.
        """
        now = datetime.now(UTC)
        now_text = now.isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = {
                key: connection.execute(
                    """SELECT window_started_at, attempts, blocked_until
                       FROM auth_login_limits WHERE bucket_key = ?""",
                    (key,),
                ).fetchone()
                for key in bucket_keys
            }
            retry_after = 0
            for row in rows.values():
                if row is not None and row["blocked_until"] is not None:
                    blocked_until = datetime.fromisoformat(row["blocked_until"])
                    retry_after = max(
                        retry_after,
                        int((blocked_until - now).total_seconds() + 0.999),
                    )
            if retry_after > 0:
                connection.rollback()
                return retry_after

            for key, row in rows.items():
                if row is None or now - datetime.fromisoformat(row["window_started_at"]) >= LOGIN_WINDOW:
                    window_started = now_text
                    attempts = 1
                else:
                    window_started = row["window_started_at"]
                    attempts = row["attempts"] + 1
                blocked_until = (now + LOGIN_BLOCK).isoformat() if attempts > LOGIN_MAX_ATTEMPTS else None
                if blocked_until is not None:
                    retry_after = max(retry_after, int(LOGIN_BLOCK.total_seconds()))
                connection.execute(
                    """INSERT INTO auth_login_limits(
                           bucket_key, window_started_at, attempts, blocked_until
                       ) VALUES (?, ?, ?, ?)
                       ON CONFLICT(bucket_key) DO UPDATE SET
                           window_started_at = excluded.window_started_at,
                           attempts = excluded.attempts,
                           blocked_until = excluded.blocked_until""",
                    (key, window_started, attempts, blocked_until),
                )
            return retry_after

    def clear_login_failures(self, bucket_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM auth_login_limits WHERE bucket_key = ?", (bucket_key,)
            )

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
            connection.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= ?", (now.isoformat(),)
            )
        return token, csrf

    def validate_session(self, token: str) -> bool:
        now = datetime.now(UTC).isoformat()
        digest = self._digest(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT expires_at FROM auth_sessions WHERE token_hash = ?", (digest,)
            ).fetchone()
            if row is None:
                return False
            if row["expires_at"] <= now:
                connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (digest,))
                return False
        return True

    def validate_csrf(self, token: str, csrf: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT csrf_hash FROM auth_sessions WHERE token_hash = ?",
                (self._digest(token),),
            ).fetchone()
        return row is not None and secrets.compare_digest(row["csrf_hash"], self._digest(csrf))

    def revoke_session(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?", (self._digest(token),)
            )
