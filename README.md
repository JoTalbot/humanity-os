# HUMANITY OS

**Open, human-centred intelligence infrastructure for the long-term benefit of humanity.**

## Mission

Expand humanity's ability to understand, learn, create, preserve knowledge, and solve shared problems while protecting human agency.

## Strategic charter

- Mission: human development, civilization development, and scientific progress.
- Stewardship: humanity as the intended beneficiary; no single company, model, or person should control the system.
- Intelligence: hybrid personal + collective.
- Access: open and free core.
- Horizon: continuous evolution without a planned end date.

## Product sequence

1. **HUMANITY ONE** — personal knowledge and intelligence workspace.
2. **HUMANITY NETWORK** — interoperable agents and federated knowledge exchange.
3. **HUMANITY CIVILIZATION** — open infrastructure for education, research, and shared problem-solving.

## First milestone

Build a useful, independently deployable personal product first. The initial release focuses on private knowledge, source-aware assistance, explicit personal memory, portability, and model-provider replaceability.

## Principles

Human agency; personal data sovereignty; open protocols; verifiable knowledge provenance; least privilege; accountable automation; independent implementations; backward-compatible evolution.

## Current implementation

The HUMANITY ONE local prototype provides private-by-default SQLite knowledge records, CRUD operations, search, cursor pagination, and versioned JSON export. It supports a single local owner identity with Argon2id password hashing, opaque 12-hour server-side sessions, logout and password-rotation revocation, CSRF checks for cookie-authenticated mutations, and persistent login throttling (five failed attempts per owner/source-IP bucket in 15 minutes trigger a 15-minute lockout). Authentication security events are recorded in a local append-only SQLite audit table without storing credentials or raw IP addresses. Configure or rotate the owner password interactively with `humanity-os --set-owner-password`. Optional shared bearer-token authentication remains available through `HUMANITY_OS_API_TOKEN`; generate a token with `humanity-os --generate-api-token`.

It also supports consistent SQLite snapshots through `humanity-os --backup-to PATH`, read-only integrity/model verification through `humanity-os --verify-backup PATH`, and guarded restore through `humanity-os --restore-from PATH --safety-backup PATH --confirm-restore`.

The API includes source/evidence provenance and an explicit human-reviewed conflict queue; conflicts are never auto-resolved. The API remains loopback-only. This is a single-owner local prototype, not a multi-user identity platform. Password recovery, MFA, session-management UI, multi-tenant isolation, general API rate limiting, safe remote deployment, independent security review, legal review, and ratified public governance are not complete. No production readiness is claimed.

See `constitution/`, `architecture/`, `specifications/` (including the knowledge provenance contract), `security/`, `federation/`, `governance/`, `product/`, `roadmap/`, and `docs/`. Run locally with `python -m pip install -e '.[dev]'` then `humanity-os`.
