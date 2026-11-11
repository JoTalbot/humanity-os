# Local development

Requires Python 3.11+.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
humanity-os
```

The API binds to `127.0.0.1:8765`; interactive OpenAPI docs are at `http://127.0.0.1:8765/docs`. The default SQLite database is `~/.humanity-os/knowledge.sqlite3`; override it with `HUMANITY_OS_DB`.

## API
- `POST /v1/knowledge`: create a private-by-default knowledge record.
- `GET /v1/knowledge?q=...`: search record content; supports pagination.
- `GET /v1/knowledge/{id}`: read one record.
- `PUT /v1/knowledge/{id}`: update a record.
- `DELETE /v1/knowledge/{id}`: delete a record.
- `GET /v1/knowledge/export`: export all records as versioned JSON.

## SQLite backup

Create a consistent SQLite snapshot using SQLite's online backup API:

```bash
humanity-os --backup-to "$HOME/humanity-backups/knowledge-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
humanity-os --verify-backup "$HOME/humanity-backups/knowledge-YYYYMMDDTHHMMSSZ.sqlite3"
```

Backup creation refuses to overwrite any existing file, creates the destination with owner-only permissions where supported, and checks SQLite integrity before reporting success. Verification opens the snapshot read-only, runs SQLite integrity checking, validates every knowledge record against the current model, and reports the record count. Backups contain personal data: store them on encrypted storage and include them in your own retention policy.

**Restore is intentionally not exposed yet.** A safe restore workflow must validate schema compatibility, create and verify a pre-restore safety snapshot, require explicit confirmation, and replace the active database atomically. Do not restore by manually copying a file over a running database.

## Security boundary

This first vertical slice has no authentication or multi-tenant isolation. The CLI refuses non-loopback binding. Do not expose it through a reverse proxy or to a LAN. Network deployment is blocked until authentication, authorisation, origin/CSRF policy as applicable, rate limits, secret handling, and threat-model review are implemented. Export and backup files contain personal data and must be stored accordingly.

## Local checks

```bash
pytest
ruff check .
``

The CI workflow runs these checks on pushes and pull requests.
