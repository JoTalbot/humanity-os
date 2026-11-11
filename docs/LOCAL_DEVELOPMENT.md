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

## Security boundary
This first vertical slice has no authentication or multi-tenant isolation. The CLI refuses non-loopback binding. Do not expose it through a reverse proxy or to a LAN. Network deployment is blocked until authentication, authorisation, origin/CSRF policy as applicable, rate limits, secret handling, and threat-model review are implemented. Export files contain personal data and must be stored accordingly.

## Local checks
```bash
pytest
ruff check .
```
These are instructions only. The checks have not been executed for this change.
