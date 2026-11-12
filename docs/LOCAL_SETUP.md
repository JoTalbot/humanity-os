# Local HUMANITY ONE Setup

## Requirements

- Python 3.11 or newer.
- A local filesystem with enough protected space for the SQLite workspace, exports and backups.
- The service is designed for one local owner and loopback access only.

## Install

From the repository root:

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
\`\`\`

## First start

Configure the owner password:

\`\`\`bash
humanity-os --set-owner-password
\`\`\`

The password must be at least 12 characters. Then start the local service:

\`\`\`bash
humanity-os --host 127.0.0.1 --port 8765
\`\`\`

Open \`http://127.0.0.1:8765/\` on the same machine and sign in.

The default database is \`~/.humanity-os/knowledge.sqlite3\`. To use another location, set \`HUMANITY_OS_DB\` before running both the password command and server. The host is loopback-only; do not bind to \`0.0.0.0\`, expose it through a reverse proxy, or forward the port to a LAN/public interface.

## Backups and portability

Stop the service before restore or portable import. Create a consistent SQLite backup:

\`\`\`bash
humanity-os --backup-to ./humanity-safety.sqlite3
humanity-os --verify-backup ./humanity-safety.sqlite3
\`\`\`

Create a portable JSON export (the destination must not already exist):

\`\`\`bash
humanity-os --export-workspace ./humanity-workspace.json
\`\`\`

A portable import replaces the active workspace only after a verified pre-import safety backup and explicit confirmation:

\`\`\`bash
humanity-os --import-workspace-from ./humanity-workspace.json \\
  --safety-backup ./before-import.sqlite3 --confirm-restore
\`\`\`

Owner credentials, live sessions and CSRF tokens are not portable. Configure a new owner password after importing a workspace. Protect the database, safety backups and portable exports as sensitive personal data. Portable JSON exports contain document text and approved/pending memory content in plaintext.

## Model providers

The constrained local Agent Runtime exposes only manually invoked local search/context tools and pending memory proposals; it does not autonomously plan or execute multi-step work.

No model provider is configured by default. Document search and context preparation are local-only. The document answer endpoint returns unavailable unless a provider is explicitly injected into the application, and each answer request still requires explicit provider-processing consent. No provider adapter or remote integration is included in this milestone.

## Operational warning

This is a development-stage local application. It has not been certified for production use, multi-user access, LAN exposure, or public hosting.
