# Local development

Requires Python 3.11+.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
humanity-os
```

The API binds to `127.0.0.1:8765`; interactive OpenAPI docs are at `http://127.0.0.1:8765/docs`. The default SQLite database is `~/.humanity-os/knowledge.sqlite3`; override it with `HUMANITY_OS_DB`.

## Owner identity and sessions

Configure the local owner password from the machine running the service:

```bash
humanity-os --set-owner-password
```

The password is entered interactively (not as a command-line argument), must contain at least 12 characters, and is stored as an Argon2id password hash. Changing it revokes every active session. There is one local owner identity in this prototype, not a multi-user account system.

Log in with `POST /auth/login` and JSON body `{"password":"..."}`. On success, the server sets an opaque, random, HttpOnly, SameSite=Strict session cookie and returns a CSRF token. Keep the CSRF token in client memory and send it as `X-CSRF-Token` on state-changing requests made with the cookie. The cookie is valid for 12 hours; logout at `POST /auth/logout` revokes the server-side session. Session tokens are stored only as SHA-256 digests. Password changes revoke all sessions.

The cookie is marked Secure when the request uses HTTPS. The service still refuses non-loopback binding. Do not place it behind a public reverse proxy or expose it to a LAN. There is no password recovery, account recovery, multi-factor authentication, login rate limiting, session management UI, or multi-user isolation yet. Protect the host account and encrypted backups. A shared bearer token remains available as an optional compatibility mechanism; prefer owner sessions for interactive clients.

## Bearer-token compatibility

Generate a cryptographically random 256-bit token with `humanity-os --generate-api-token`, then set `HUMANITY_OS_API_TOKEN` in the server environment. If configured, protected API routes accept that bearer token. Never commit or log it.

## API

- `POST /auth/login`: create an owner session.
- `POST /auth/logout`: revoke the current session (requires CSRF header).
- `GET /health`: health status.
- `POST /v1/knowledge`: create a private-by-default knowledge record.
- `GET /v1/knowledge?q=...`: search record content; supports pagination.
- `GET /v1/knowledge/{id}`: read one record.
- `PUT /v1/knowledge/{id}`: update a record.
- `DELETE /v1/knowledge/{id}`: delete a record.
- `GET /v1/knowledge/export`: export all records as versioned JSON.

When no owner password or bearer token is configured, the prototype remains unauthenticated and loopback-only. Once an owner password is set, all protected routes require a valid owner session or configured bearer token. Cookie-authenticated state-changing requests require a valid CSRF token.

## SQLite backup

Create and verify a consistent snapshot:

```bash
humanity-os --backup-to "$HOME/humanity-backups/knowledge-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
humanity-os --verify-backup "$HOME/humanity-backups/knowledge-YYYYMMDDTHHMMSSZ.sqlite3"
```

Backup creation refuses to overwrite an existing file, creates it with owner-only permissions where supported, and checks SQLite integrity. Verification checks SQLite integrity and validates every stored knowledge record. Backups contain personal data; store them on encrypted storage.

Stop the server before restore:

```bash
humanity-os --restore-from "$HOME/humanity-backups/known-good.sqlite3" \
  --safety-backup "$HOME/humanity-backups/pre-restore-$(date -u +%Y%m%dT%H%M%SZ).sqlite3" \
  --confirm-restore
```

Restore validates the source, creates a non-overwriting safety snapshot, stages and verifies the replacement, then atomically replaces the active database. It is a local CLI operation, not a network endpoint.

## Security and dependency maintenance

CI runs Ruff, pytest and `pip-audit`. Dependabot checks Python dependencies and GitHub Actions weekly. These checks do not replace code review or independent security assessment.

## Security boundary

This is a local, single-owner prototype. It has no multi-tenant isolation, password recovery, MFA, login throttling, session UI, remote deployment hardening, rate limiting, or independent security review. The CLI refuses non-loopback binding. Do not expose it through a reverse proxy or to a LAN. Export and backup files contain personal data.

## Local checks

```bash
pytest
ruff check .
pip-audit
```
