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

The cookie is marked Secure when the request uses HTTPS. The ASGI application itself rejects every non-loopback peer, including requests to `/health`; the CLI also refuses non-loopback bind addresses. This second check is intentional: starting the exported ASGI app directly with Uvicorn must not bypass the network boundary. Do not place it behind a public reverse proxy or expose it to a LAN. There is no password recovery, account recovery, multi-factor authentication, session management UI, general API rate limiting, or multi-user isolation yet. Protect the host account and encrypted backups. A shared bearer token remains available as an optional compatibility mechanism; prefer owner sessions for interactive clients.

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
- `GET /v1/knowledge/export`: export knowledge records only (legacy, incomplete interchange format).
- `GET /v1/workspace/export`: authenticated, versioned workspace export with provenance, revisions, decisions, claim graph, assessments, reasoning history and security audit metadata.

Authentication is fail-closed by default: if neither an owner password nor a bearer token is configured, every protected route returns `401`; `/health` remains available to loopback clients. Configure the owner password locally with the CLI before using the API. Once an owner password is set, protected routes require a valid owner session or configured bearer token. Cookie-authenticated state-changing requests require a valid CSRF token. The `allow_unauthenticated_local=True` app-factory option exists only for isolated automated tests and must never be enabled in a deployed service.

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

This is a local, single-owner prototype. It has no multi-tenant isolation, password recovery, MFA, session UI, remote deployment hardening, general API rate limiting, or independent security review. Both the CLI and ASGI middleware enforce loopback-only access. Direct ASGI/Uvicorn startup does not bypass the restriction. Do not expose it through a reverse proxy or to a LAN. Export and backup files contain personal data.

## Local checks

```bash
pytest
ruff check .
pip-audit
```

## Portable workspace export and deletion

The full export endpoint is `GET /v1/workspace/export`. It is protected by the normal owner-session or bearer-token boundary and returns format `humanity-os-workspace`, schema version `1.0.0`, a UTC export timestamp and a SHA-256 digest over the canonical document before the integrity block is added. The export includes domain tables and security audit metadata. It intentionally excludes owner password hashes, active session/CSRF token hashes, login-throttling buckets, environment bearer tokens, SQLite internals and derived indexes. Do not treat the legacy knowledge-only export as a complete workspace export.

Create a portable export from the machine running the service:

```bash
humanity-os --export-workspace "$HOME/humanity-backups/workspace-$(date -u +%Y%m%dT%H%M%SZ).json"
```

The command refuses to overwrite an existing path and creates the file with owner-only permissions where supported. The digest detects accidental changes; it is not a digital signature and does not prove who created the export.

Full workspace deletion is an offline, destructive CLI operation. Stop the HUMANITY OS service first, then run:

```bash
humanity-os --delete-workspace \
  --safety-backup "$HOME/humanity-backups/pre-delete-$(date -u +%Y%m%dT%H%M%SZ).sqlite3" \
  --confirm-delete
```

The command creates and verifies a separate non-overwriting SQLite safety backup before deleting the active database and its `-wal` and `-shm` sidecars. It refuses symlinked database paths. There is no HTTP deletion endpoint. The retained safety backup is a deliberate recovery copy, so deletion is not complete erasure while that backup exists. Other copies, filesystem snapshots, host-level backups, exports and storage-provider retention are outside this command's control and must be managed separately. Store backups encrypted, restrict access, and apply a documented retention period. The command cannot guarantee cryptographic erasure from SSDs, snapshots or external backup systems.
