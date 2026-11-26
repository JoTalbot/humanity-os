# Knowledge Conflict Review Contract 0.1

## Purpose

Conflicting knowledge must be represented explicitly rather than silently overwriting one statement or asking a model to choose a winner.

## Lifecycle

A conflict links two distinct existing knowledge records and a human-readable reason.

- `pending_review`: created and awaiting an accountable human review.
- `resolved`: a reviewer recorded a resolution note.
- `dismissed`: a reviewer determined that the reported conflict should not be treated as an active contradiction and recorded why.

Only pending conflicts accept a decision. Every decision requires a non-empty resolution note. A second decision is rejected. The current single-owner prototype treats the authenticated owner as the decision authority; a multi-user implementation must persist reviewer identity and role.

## Invariants

- A record cannot conflict with itself.
- The pair is stored in canonical ID order, so reversed duplicates are rejected.
- Both records must exist at creation time.
- Creation never changes either source record.
- The system does not auto-resolve conflicts or infer truth from recency, popularity, or model confidence.
- Conflicts and their status are included in SQLite backups and validated during backup verification.
- A knowledge record referenced by a conflict cannot be deleted until the conflict is explicitly reviewed and removed through a future governed workflow. SQLite foreign-key enforcement prevents orphaned conflict records; the current API returns HTTP 409 rather than silently deleting either side.

## API

- `POST /v1/conflicts`: create a pending conflict.
- `GET /v1/conflicts`: list conflicts, optionally filtered by status.
- `POST /v1/conflicts/{id}/decision`: record a human resolution or dismissal with a required note.

## Limitations

The current API is a local single-owner review queue. It does not provide multi-reviewer quorum, appeals, signed decisions, immutable decision history, or automatic contradiction detection. Those require separate contracts and governance.
