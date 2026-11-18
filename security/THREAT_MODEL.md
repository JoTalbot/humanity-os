# Security Threat Model 0.1

## Assets
Personal data, credentials, keys, private knowledge, agent permissions, federation trust, audit history, software supply chain and availability.

## Threats and controls

- Prompt injection: retrieved content is untrusted data; isolate instructions from data.
- Excessive agent authority: capability allowlists, short-lived scoped grants, approval gates.
- Provider leakage: data classification, minimisation, provider disclosure and local-model option.
- Account takeover: Argon2id password hashes, opaque server-side sessions, 12-hour expiry, logout revocation, password-rotation revocation, HttpOnly/SameSite=Strict cookies and CSRF token validation for cookie-authenticated mutations.
- Session database theft: only SHA-256 digests of random 256-bit session tokens and CSRF tokens are stored; host/database access remains security-critical.
- Brute force: five failed attempts per owner and source-IP bucket within a 15-minute window trigger a 15-minute lockout; successful login clears both counters. Client IP is taken from the direct ASGI peer, not an untrusted forwarded header. Distributed attacks and denial-of-service lockout still require edge controls.
- Authentication audit: password changes, login failures/successes, rate limiting, session creation and revocation are recorded without credentials or raw IP addresses. SQLite triggers reject event updates and deletes; this is application-level tamper resistance, not protection against an attacker with full database-file control.
- Shared-token disclosure: optional bearer token, cryptographic token generation, constant-time comparison and environment/secret-manager injection.
- Anonymous API exposure: authentication is fail-closed by default when no owner password or bearer token exists; protected routes return 401. The unauthenticated mode is an explicit app-factory option reserved for isolated tests.
- Network-boundary bypass: both the CLI bind validation and ASGI middleware enforce loopback-only access. The ASGI middleware checks the actual peer address for every route, including health, so direct Uvicorn startup cannot silently expose the prototype.
- Federation spoofing: signed node identity, key rotation and revocation.
- Malicious update: reproducible builds, signed releases, provenance and review.
- Audit tampering: append-only design, external checkpoints and access separation.
- Data loss/ransomware: SQLite backup creation and integrity verification are implemented; restore is covered by automated tests. Application-level backup encryption is not implemented, so backup files require host/storage-layer access controls and encryption where appropriate.
- Incomplete export: the full workspace export uses an explicit allowlist covering domain records, provenance, immutable history, reasoning and security audit metadata; credential/session material and live secrets are excluded.
- Destructive deletion: full workspace deletion is offline-only, requires explicit confirmation and a separate verified pre-deletion backup, and removes the active SQLite database plus WAL/SHM sidecars. Retained backups, snapshots and external copies remain outside the deletion boundary.
- Hallucinations: evidence references, uncertainty labels and independent verification.
- Denial of service: quotas, rate limits and graceful degradation.

## Invariants
Private by default; no self-escalation; external side effects authorised and audited; secrets excluded from prompts/logs by default; federation opt-in and revocable; security failure stops the affected operation.

## Release gates
The owner identity and session implementation is single-user local functionality, not a complete identity platform. Password recovery, MFA, session inspection/revocation UI, multi-user isolation, general API rate limits, origin policy, TLS/edge configuration, and comprehensive secret-scanning controls remain incomplete. Dependency vulnerability auditing is part of the configured CI workflow. Independent security review is not required or planned as a release gate. The API must remain loopback-only, and protected routes must remain authenticated by default. Do not expose it to a LAN or public internet.

Before broad public deployment: complete the configured automated RC validation, export/deletion verification, incident response planning, privacy/legal decisions and a public residual-risk register. Manual operator acceptance, including a clean-machine restore walkthrough, is deferred by owner and is not a current development gate. Workspace deletion is not a claim of cryptographic erasure; retained safety backups and external copies require separate retention and disposal controls.

## Document ingestion risks

The current ingestion endpoint accepts only bounded UTF-8 `.txt`, `.md`, and `.markdown` content. It does not parse archives, PDFs, DOCX, images, macros, or HTML, and does not fetch remote URLs. Markdown must remain inert text and must not be rendered as trusted HTML. Document content and chunks are sensitive local data and are included in portable exports. Future binary parsers require decompression limits, parser sandboxing, malformed-file fuzzing, and separate security review.

## Explicit memory risks

The memory API separates pending proposals from approved memory. Only a distinct authenticated owner approval endpoint creates durable memory; model generation and document retrieval do not call that endpoint. Proposal approval, rejection, archive and restore events are append-only. Portable exports include pending proposals and approved memory content, so exports and backups remain sensitive. This milestone does not provide multi-user approval, cryptographic signatures, per-item deletion, or independent security certification.

## Retrieved-content and prompt-injection risks

The `/v1/answers/context` endpoint returns source excerpts as untrusted data with document/chunk identifiers, hashes and offsets. A source may contain adversarial instructions or misleading content. A future model caller must preserve a strict separation between trusted system policy and retrieved excerpts, must not treat excerpts as instructions, and must not grant them tool permissions. The context endpoint itself does not call a model or execute source content. Its manifest SHA-256 detects accidental modification but is not a signature or authenticity proof.

Citation validation checks that cited source excerpts match the current local manifest and chunk records. It does not establish truth, source reliability, independence or logical entailment. A valid provenance result must never be presented as proof that an answer is factually correct. The validator does not persist answer text.


## Constrained agent runtime

Agent tools are statically allowlisted and one tool is invoked per explicit authenticated request. Tool inputs and outputs are bounded; run history stores digests and metadata rather than raw content. Memory proposals remain pending until a separate owner approval request. Each run is owned by a process-specific worker ID and a bounded UTC lease; configured lease durations reject non-finite, non-positive and boolean values. Conditional lease renewal, expiry recovery and terminal transitions are serialized with SQLite write transactions; stale workers cannot finish a recovered run. Same-host multi-process coordination is supported only when workers share one local SQLite database on a filesystem with reliable locking. Multi-host, network-filesystem and mixed-version rolling-upgrade deployments are unsupported. Leases use the shared host's UTC wall clock without skew compensation, so clock steps can cause early expiry or delayed recovery. This is not an OS sandbox. No shell, arbitrary code, filesystem write, network fetch, credential access, or provider activation tool is exposed.
