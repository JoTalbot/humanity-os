# Data Retention and Disposal Policy 0.1

This policy describes what the local prototype retains and what its export and deletion commands can actually remove. It is an operator policy, not an automated retention engine.

## Retention classes

| Data class | Default behavior | Operator responsibility |
| --- | --- | --- |
| Active workspace database | Retained until the owner deletes or replaces it | Protect the host and database; keep the service local-only |
| Knowledge revisions, decisions, claims and assessments | Append-only history; no automatic expiry | Treat as user-owned workspace history; export before destructive changes |
| Authentication audit events | Append-only and included in portable exports | Review privacy needs before sharing an export; events contain metadata, not credentials or raw IP addresses |
| Password hashes, sessions, CSRF hashes and login limits | Stored only in the local database; excluded from portable exports | Reconfigure the owner password after portable import; do not copy live database files casually |
| Portable JSON exports | Remain until manually deleted | Encrypt storage, restrict access, and remove obsolete copies |
| SQLite backups and pre-operation safety backups | Remain until manually deleted; the application does not expire them | Verify backups, retain at least one encrypted offline recovery copy, and delete obsolete copies under owner control |
| SQLite WAL/SHM sidecars | Managed by SQLite while the database is active | Never delete live sidecars; stop the service and create a verified backup before offline disposal |
| OS snapshots, cloud/provider backups and other external copies | Outside application control | Configure retention and deletion with each host, filesystem and provider |
| Application/service logs | Outside the workspace export | Configure host log rotation and ensure secrets are not logged |

## Recommended operator baseline

For a single-owner local node, the suggested starting policy is:

- Keep routine encrypted backups for 30 days.
- Keep at least one verified offline backup while the workspace is in active use.
- Keep a pre-import or pre-deletion safety backup until the owner has verified the resulting state and explicitly decides whether to retain or delete that recovery copy.
- Remove obsolete portable exports and backups manually after confirming that another required recovery copy exists.
- Review external snapshots and provider retention separately; deleting the active database does not delete those copies.

These are recommendations, not enforced defaults. HUMANITY OS 0.1 performs no automatic backup expiry or retention-based deletion.

## Deletion boundaries

The offline `--delete-workspace` command requires a separate verified safety backup and explicit confirmation. It removes the active SQLite database and its `-wal` and `-shm` sidecars after the operator stops the service. It does not remove the safety backup, portable exports, copied databases, filesystem snapshots, provider backups, host logs or storage-media remanence.

Portable import replaces the active database only after creating a verified pre-import backup. It does not migrate owner credentials or active sessions. A new owner password must be configured after import.

The project does not claim cryptographic erasure, physical-media sanitization or deletion from external backup systems. Where stronger disposal is required, operators must use encrypted storage and follow the host/provider's documented key-destruction and retention controls.

## Release boundary

A future release may add a reviewed retention configuration and auditable backup inventory. Automatic deletion must not be introduced until retention defaults, recovery guarantees, backup discovery and owner approval behavior have explicit contracts and tests.

## Document content

Text and Markdown document originals and extracted chunks are stored in the active SQLite database and included in portable workspace exports (schema 1.1.0). Export files and safety backups therefore contain the full document text. The current prototype has no per-document deletion or automatic retention expiry; protect and dispose of the database, exports and backups as sensitive personal data.

## Explicit memory

Pending memory proposals, approved memory items and append-only lifecycle events are stored in the local SQLite database and included in workspace exports (schema 1.3.0). Archiving changes visibility in the memory lifecycle but does not erase content or event history. The current prototype has no memory deletion or automatic expiry workflow.

## Agent audit metadata

Agent runs and invocation events are stored in the workspace and included in portable exports (schema 1.3.0). Raw tool arguments and raw results are not stored in agent run history; SHA-256 digests, agent/tool IDs, statuses, timestamps and error class codes are retained. The current prototype has no per-run deletion or audit-retention expiry.
