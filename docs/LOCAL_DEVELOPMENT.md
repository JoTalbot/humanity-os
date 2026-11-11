# Local development

Requires Python 3.11+.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
humanity-os
```

The API binds to `127.0.0.1:8765`; interactive OpenAPI docs are at `http://127.0.0.1:8765/docs`. The default SQLite database is `~/.humanity-os/knowledge.sqlite3`; override it with `HUMANITY_OS_DB`.

## Security boundary
This first vertical slice has no authentication or multi-tenant isolation. The CLI refuses non-loopback binding. Do not expose it through a reverse proxy or to a LAN. Network deployment is blocked until authentication, authorisation, origin/CSRF policy as applicable, rate limits, secret handling, and threat-model review are implemented.

## Local checks
```bash
pytest
ruff check .
```
These are instructions only. The checks have not been executed for this change.
