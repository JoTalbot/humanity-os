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

Restore is available as an explicit CLI operation. **Stop the HUMANITY OS server before restoring** so no process has the database open:

```bash
humanity-os --restore-from "$HOME/humanity-backups/known-good.sqlite3" \
  --safety-backup "$HOME/humanity-backups/pre-restore-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
  --confirm-restore
```

The command validates SQLite integrity and every record before changing the active database, creates a new non-overwriting snapshot of the current database, stages the incoming database beside the active file, validates the staged copy, and only then replaces the active database atomically. If validation fails, the active database is left untouched. The safety snapshot is retained even if the staged replacement fails. Restore is local CLI only; there is no network restore endpoint. Do not manually copy a database over a running server.

## Security boundary

This first vertical slice has no authentication or multi-tenant isolation. The CLI refuses non-loopback binding. Do not expose it through a reverse proxy or to a LAN. Network deployment is blocked until authentication, authorisation, origin/CSRF policy as applicable, rate limits, secret handling, and threat-model review are implemented. Export and backup files contain personal data and must be stored accordingly.

## Local checks

```bash
pytest
ruff check .
``

The CI workflow runs these checks on pushes and pull requests.
