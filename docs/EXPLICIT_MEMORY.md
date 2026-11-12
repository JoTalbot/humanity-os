# Explicit Memory 0.1

## Contract

HUMANITY ONE separates a memory proposal from durable memory. Creating a proposal does not make it retrievable as approved memory and does not change any existing memory. Only a distinct authenticated owner action, \`POST /v1/memory/proposals/{id}/approve\`, promotes a pending proposal into an active memory item.

The proposal captures a bounded title, content, rationale, and optional source document/chunk pair. If a source is supplied, the exact chunk must belong to the stated document. Source references remain attached to the approved memory.

## Lifecycle API

- \`POST /v1/memory/proposals\`: create a pending proposal.
- \`GET /v1/memory/proposals\` and \`GET /v1/memory/proposals/{id}\`: inspect proposals.
- \`POST /v1/memory/proposals/{id}/approve\`: explicit owner approval; creates durable memory.
- \`POST /v1/memory/proposals/{id}/reject\`: explicit rejection; does not create memory.
- \`GET /v1/memories\` and \`GET /v1/memories/{id}\`: inspect approved memory.
- \`POST /v1/memories/{id}/archive\` and \`/restore\`: explicit lifecycle changes.
- \`GET /v1/memory/events\`: inspect append-only lifecycle events.

Approved memory content is immutable in this milestone. A material change requires a new proposal and a separate approval. Duplicate content is rejected. Archive/restore changes status but never erases the content or event history.

## Safety invariants

1. Model generation, document ingestion, retrieval, and search have no approval capability.
2. Proposal creation is not approval.
3. Approval is a separate authenticated HTTP request.
4. Only pending proposals can be approved or rejected, once.
5. Every proposal, approval, rejection, archive, and restore is recorded in an append-only event table.
6. Portable export schema 1.3.0 includes proposals, approved memories, and events; import validates proposal-to-memory linkage and content hashes.
7. Legacy export schemas 1.0.0 and 1.1.0 remain importable with empty memory tables.

## Privacy and limitations

Memory is stored locally in SQLite and included in plaintext portable exports and backups. Protect those files as sensitive personal data. This prototype has no multi-user roles, delegated approvals, cryptographic signing, encrypted export, semantic memory retrieval, automated retention, or memory deletion workflow. It is not a legal compliance or production-readiness claim.
