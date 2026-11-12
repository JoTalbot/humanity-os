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
- Data loss/ransomware: encrypted backups and tested restore.
- Incomplete export: the full workspace export uses an explicit allowlist covering domain records, provenance, immutable history, reasoning and security audit metadata; credential/session material and live secrets are excluded.
- Destructive deletion: full workspace deletion is offline-only, requires explicit confirmation and a separate verified pre-deletion backup, and removes the active SQLite database plus WAL/SHM sidecars. Retained backups, snapshots and external copies remain outside the deletion boundary.
- Hallucinations: evidence references, uncertainty labels and independent verification.
- Denial of service: quotas, rate limits and graceful degradation.

## Invariants
Private by default; no self-escalation; external side effects authorised and audited; secrets excluded from prompts/logs by default; federation opt-in and revocable; security failure stops the affected operation.

## Release gates
The owner identity and session implementation is single-user local functionality, not a complete identity platform. Password recovery, MFA, session inspection/revocation UI, multi-user isolation, general API rate limits, origin policy, TLS/edge configuration, audit events, dependency/secret scanning and independent review remain incomplete. The API must remain loopback-only, and protected routes must remain authenticated by default. Do not expose it to a LAN or public internet.

Before broad public deployment: independent security review, restore demonstration, export/deletion verification, incident response plan, privacy/legal review and public residual-risk register. Workspace deletion is not a claim of cryptographic erasure; retained safety backups and external copies require separate retention and disposal controls.

## Document ingestion risks

The current ingestion endpoint accepts only bounded UTF-8 `.txt`, `.md`, and `.markdown` content. It does not parse archives, PDFs, DOCX, images, macros, or HTML, and does not fetch remote URLs. Markdown must remain inert text and must not be rendered as trusted HTML. Document content and chunks are sensitive local data and are included in portable exports. Future binary parsers require decompression limits, parser sandboxing, malformed-file fuzzing, and separate security review.

## Explicit memory risks

The memory API separates pending proposals from approved memory. Only a distinct authenticated owner approval endpoint creates durable memory; model generation and document retrieval do not call that endpoint. Proposal approval, rejection, archive and restore events are append-only. Portable exports include pending proposals and approved memory content, so exports and backups remain sensitive. This milestone does not provide multi-user approval, cryptographic signatures, per-item deletion, or independent security certification.

## Local browser interface

The root login page and static assets are exempt from API authentication only to make the sign-in screen reachable; they remain behind the ASGI loopback peer boundary. All workspace data APIs remain authenticated. The browser keeps the CSRF token in volatile page memory only and makes same-origin requests. No remote scripts, fonts, analytics or CDNs are used. A future remote-access mode requires a new threat model, secure transport, origin/CSRF review and independent security assessment.

## Source context assembly

The context-preparation endpoint performs local lexical retrieval only and reports that no model call or external processing occurred. It bounds passage count and context characters and carries source document/chunk IDs, hashes and exact excerpt offsets. A future provider-backed answer flow must add explicit disclosure and consent for any external data transfer; this endpoint must not be treated as that consent.

## Provider-backed document answers

The document answer endpoint requires a distinct per-request provider-processing consent flag before retrieved source passages are passed to an injected model provider. The default application has no provider. Provider/model identifiers are disclosed through a capabilities endpoint, but provider locality and behavior are not independently attested. Citation-label checks only verify that returned labels map to retrieved passages; they do not establish semantic entailment or source truth. A future real provider integration requires a provider-specific data-flow review and security assessment.

## Constrained Agent Runtime

The initial runtime permits one explicitly requested local tool invocation at a time. Profiles have static allowlists for knowledge/document reads and pending memory proposal creation. No profile can approve memory. No shell, arbitrary code, filesystem write, network fetch, credential access, provider activation or external side-effect tool is registered. Tool arguments/results are bounded. Run history stores hashes and minimal metadata, not raw arguments or outputs; event records are append-only. This is not OS-level sandboxing and does not establish production safety.
