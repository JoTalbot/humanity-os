# HUMANITY ONE 0.1 — Operator Acceptance Runbook

This procedure is for a **disposable test workspace on a clean machine**. Do not use a production or only-copy workspace. The 0.1 prototype is local-only and must not be exposed to a LAN, reverse proxy, or public network.

## 1. Record the test environment

Record the date, OS and version, architecture, Python version (3.11+), install method, commit or package version, and operator. Confirm the machine has encrypted storage for any test exports and backups.

## 2. Install and initialize

For a candidate-branch acceptance run, clone the exact branch under test and record its commit SHA:

```bash
git clone --branch fix/agent-lease-side-effects-audit --single-branch \
  https://github.com/JoTalbot/humanity-os.git
cd humanity-os
git rev-parse HEAD
mkdir -p "$HOME/humanity-acceptance/backups"
export HUMANITY_OS_DB="$HOME/humanity-acceptance/workspace.sqlite3"
python -m venv "$HOME/humanity-acceptance/venv"
. "$HOME/humanity-acceptance/venv/bin/activate"
python -m pip install '.[dev]'
```

For an artifact acceptance run, install the exact wheel produced by the candidate CI instead of installing from the source checkout. Record the artifact filename, SHA-256 and source commit. Do not use an unrelated package-index release. Do not put passwords or bearer tokens in shell arguments, shell history, CI logs, or screenshots.

Set the owner password interactively:

```bash
humanity-os --set-owner-password
```

Start the application in the same environment:

```bash
humanity-os
```

Open `http://127.0.0.1:8765/`. Verify that the login screen appears, an incorrect password is rejected, the configured owner can log in, and logout returns the UI to the login state. Confirm the service is reachable only through loopback.

## 3. Create disposable test data

Through the UI, create:
- one knowledge note with a unique marker such as `acceptance-note-<date>`;
- one small UTF-8 text or Markdown document with a different unique marker;
- one memory proposal, approve it, then archive it.

Verify that the note and document can be found, source context identifies the expected source, and the approved memory shows its archived state and lifecycle history. Do not use real personal or confidential content.

## 4. SQLite backup and restore

Stop the server cleanly. Create and verify a backup:

```bash
humanity-os --backup-to "$HOME/humanity-acceptance/backups/baseline.sqlite3"
humanity-os --verify-backup "$HOME/humanity-acceptance/backups/baseline.sqlite3"
```

Restart the service and add a second disposable note with a unique marker. Stop the service again, then restore the baseline backup into the same dedicated database:

```bash
humanity-os --restore-from "$HOME/humanity-acceptance/backups/baseline.sqlite3" \
  --safety-backup "$HOME/humanity-acceptance/backups/pre-restore.sqlite3" \
  --confirm-restore
humanity-os --verify-backup "$HOME/humanity-acceptance/backups/pre-restore.sqlite3"
```

Restart the service. Verify the baseline note, document and archived memory are present; verify the second note added after the baseline is absent. Confirm the pre-restore backup exists and verifies. Record the result and observed downtime.

## 5. Portable export and import on a second clean workspace

Stop the service and export the source workspace:

```bash
humanity-os --export-workspace "$HOME/humanity-acceptance/backups/workspace.json"
```

Create a second isolated database path and configure it for the import target:

```bash
export HUMANITY_OS_DB="$HOME/humanity-acceptance/imported.sqlite3"
```

Initialize an empty target database by starting and stopping the app once, or use the supported owner setup workflow as documented. Import the portable export:

```bash
humanity-os --import-workspace-from "$HOME/humanity-acceptance/backups/workspace.json" \
  --safety-backup "$HOME/humanity-acceptance/backups/pre-import.sqlite3" \
  --confirm-restore
humanity-os --verify-backup "$HOME/humanity-acceptance/backups/pre-import.sqlite3"
humanity-os --set-owner-password
```

Start the service against the imported database and sign in with the newly configured owner password. Verify the note, document content, archived memory state, and lifecycle events. Confirm that owner credentials and active sessions were not imported, and that the source export remains unchanged. Record whether the target needed any manual repair.

## 6. Failure and recovery checks

For each invalid or interrupted operation that is safe to simulate on disposable data, record:
- the exact command and exit status;
- whether the active database remained usable and unchanged;
- whether a safety backup was created and verifies;
- the recovery steps and time required.

Do not simulate power loss, filesystem corruption, or process termination against a valuable workspace. Those require a separate disposable VM or filesystem snapshot and an explicitly designed fault-injection procedure.

## 7. Deletion boundary

Deletion is not required to prove backup/restore acceptance. If deletion is separately tested, use only the disposable workspace, stop the service, and retain the verified safety backup outside the database directory. Follow the explicit command and limitations in [Local development](LOCAL_DEVELOPMENT.md) and [Data retention](DATA_RETENTION.md). Confirm the active database and SQLite sidecars are gone, and separately confirm that the retained backup still verifies. Do not claim erasure of exports, snapshots, provider backups, host logs, or storage-media remnants.

## 8. Acceptance record

A run is **PASS** only when all applicable checks above have evidence. Otherwise mark it **FAIL** or **BLOCKED**, preserve logs without secrets, and record the exact failing step.

| Field | Result |
| --- | --- |
| Operator / date | |
| OS / version / architecture | |
| Python version | |
| Install method / artifact SHA-256 | |
| Application commit / version | |
| Login, logout and loopback boundary | |
| Knowledge and document workflow | |
| Memory lifecycle and provenance | |
| SQLite backup and verification | |
| SQLite restore and pre-restore backup | |
| Portable export/import on second workspace | |
| New owner credential after import | |
| Recovery / downtime observations | |
| Overall result (PASS / FAIL / BLOCKED) | |
| Evidence location (no secrets or private content) | |

A completed CI run is necessary but does not replace this operator acceptance. Do not mark clean-machine acceptance complete until a human operator executes the procedure on the supported target operating systems and records the evidence.
