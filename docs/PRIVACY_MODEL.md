# Privacy Model 0.1

## Scope and assumptions

HUMANITY OS 0.1 is a single-owner, local-first prototype. It is not a hosted multi-tenant service. Its default API boundary is loopback-only and authentication is required by default. The owner is responsible for operating-system access, device encryption, backup storage, and any network or reverse-proxy configuration around the host.

The project's mission and humanity-ownership direction do not establish a legal ownership structure, data-controller status, or a guarantee of confidentiality. Governance, jurisdiction, legal basis, and institutional accountability remain open decisions.

## Data categories

| Category | Examples | 0.1 handling |
| --- | --- | --- |
| Workspace content | Knowledge records, text/Markdown documents, document chunks, pending memory proposals, approved memory, claims, decisions | Stored locally; private visibility is the default |
| Provenance | Sources, evidence links, excerpts, locators and derivation lineage | Stored with associated knowledge |
| Historical records | Revisions, conflict decisions, evidence/claim assessments, reasoning runs | Append-only where implemented; included in portable export |
| Security audit metadata | Event type, timestamp and bounded subject | Stored locally and included in portable export; does not include password or session tokens |
| Authentication secrets | Argon2id password hash, session/CSRF token hashes, login throttle buckets | Stored locally; excluded from portable JSON export |
| Runtime secrets | Optional bearer token from environment configuration | Not stored in workspace tables; excluded from export |
| Derived/runtime data | SQLite indexes, schema internals, temporary files, process state | Recreated by the application or managed by the operator; not part of portable export |
| Operational copies | SQLite backups, portable exports, filesystem snapshots and host logs | Outside automatic lifecycle management; operator controls access and retention |

## Data flow boundaries

- The 0.1 application does not upload workspace content to a HUMANITY OS cloud service. Document ingestion is limited to bounded UTF-8 text and Markdown; it does not fetch URLs, execute Markdown/HTML, or call model providers.
- The authenticated `/v1/answers/context` endpoint assembles bounded evidence from local chunks only. It returns source IDs, hashes and offsets; it does not call a model, persist prompts, or write memory. Retrieved text is untrusted data and may contain prompt injection. See [ANSWER_CONTEXT.md](ANSWER_CONTEXT.md).
- Memory proposals are not durable memory. Only a separate authenticated owner approval request creates an active memory item; model generation and document retrieval have no approval path. See [EXPLICIT_MEMORY.md](EXPLICIT_MEMORY.md).
- The model gateway contract is present, but no provider is configured by default and no network-backed provider is included. Any future provider connection must be explicit, documented, opt-in, and disclose the exact data sent. See [MODEL_GATEWAY.md](MODEL_GATEWAY.md).
- The local API is loopback-only. A future remote-access mode requires a separate threat model, secure transport, identity, session, abuse-control and deployment review.
- Logs and backups are controlled by the host and operator. Operators must not place passwords, bearer tokens, session cookies or raw private content in logs or unprotected backup locations.

## Export and import

The versioned workspace export schema 1.2.0 contains domain records, provenance, text/Markdown document content and chunks, pending memory proposals, approved memory and lifecycle events, append-only history, reasoning records and security audit metadata. Schema 1.0.0 and 1.1.0 exports remain importable. Document text is included in plaintext and must be protected like other private workspace content. It excludes owner identity/password hashes, session and CSRF hashes, login throttling buckets, environment bearer tokens, derived indexes and SQLite implementation metadata.

The export's SHA-256 digest detects accidental modification; it is not a signature, encryption, identity proof or authenticity guarantee. Anyone with access to an export can read its included personal content. Store exports encrypted and restrict access.

Portable import validates the version, exact table set, table columns, row shapes, digest, domain payloads and foreign-key integrity in a staging database. It creates a verified safety backup before replacing the active database. Authentication identity and live sessions are reset; configure a new owner password after import.

## Deletion and retention

Workspace deletion is an offline CLI operation requiring explicit confirmation and a verified pre-deletion safety backup. The service must be stopped. The command removes the active SQLite database and its WAL/SHM sidecars after checkpointing the WAL.

This is not total erasure. The safety backup is deliberately retained, and portable exports, copied databases, snapshots, provider backups, host logs and storage-media remnants are outside the application's deletion boundary. See [DATA_RETENTION.md](DATA_RETENTION.md) for operator guidance. 0.1 does not enforce automatic retention expiry or cryptographic erasure.

## User rights and governance limitations

0.1 provides owner-controlled local export, import and workspace deletion. It does not provide multi-user access controls, delegated data-subject workflows, automated legal holds, formal consent management, jurisdiction-specific compliance guarantees, or independent certification. These are release blockers for deployments that require them.

## Design principles

1. Minimize collection and external transmission.
2. Keep personal workspace content local by default.
3. Separate user content from authentication secrets.
4. Make export scope and deletion boundaries explicit.
5. Preserve auditability without exporting live credentials.
6. Require explicit owner action for destructive operations.
7. Do not claim stronger privacy, security, or erasure properties than the implementation demonstrates.
