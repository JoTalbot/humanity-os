# Knowledge Revision History Contract 0.1

## Purpose

Knowledge is a changing body of claims, observations, procedures, and evidence. Updating a record must not silently erase the state that informed an earlier decision.

## Identity and numbering

- A knowledge record keeps one stable record ID.
- Its current payload exposes a positive, monotonically increasing `revision`, starting at 1.
- Every successful update increments the revision exactly once.
- Revision numbers are unique per record and ordered; concurrent updates serialize in SQLite before allocating the next number.

## Immutable snapshots

Each revision stores the complete validated knowledge record as it existed at that point, including title, content, kind, language, visibility, source metadata, evidence, timestamps, and revision number. Revision metadata records the actor (`owner` or `system`), timestamp, and a non-empty change reason.

Revision rows are append-only by application behavior: updates insert a new row and never rewrite earlier snapshots. This 0.1 contract does not yet add database triggers against direct local database tampering; the local database remains under the machine owner's control.

## API

- `GET /v1/knowledge/{record_id}/revisions` returns newest-first snapshots, with a bounded limit of 1–100.
- Missing parent records return 404.
- Existing `PUT /v1/knowledge/{record_id}` remains compatible and creates a revision automatically. When no reason is supplied, the reason is `updated via API`.
- Initial creation records revision 1 with actor `system` and reason `record created`.

## Backup and migration

Revision rows are included in ordinary SQLite backups and restore snapshots. Backup verification validates every stored revision payload. Existing databases and legacy backups without the revision table remain readable; schema initialization creates the missing table. Historical revisions cannot be reconstructed for changes made before this feature existed. A legacy record begins its revision history when first updated after migration; its initial current state is not retroactively represented as an authentic historical snapshot.

## Boundaries

This is local single-owner history, not a tamper-proof external ledger. Actor identity is currently coarse (`owner` when an owner password is configured, otherwise `system`). Multi-user attribution, explicit user-supplied change reasons, retention policy, tombstones, cryptographic chaining, and independent audit anchoring are future work.
