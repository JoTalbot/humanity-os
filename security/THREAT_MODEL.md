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
