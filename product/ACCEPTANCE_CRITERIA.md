# HUMANITY ONE 0.1 — Acceptance Criteria

## Installation
- [ ] Clean local deployment works from documented instructions.
- [ ] No committed secrets.
- [ ] Upgrade and rollback are documented.

## Identity and privacy
- [x] One local owner password can be set interactively without exposing it in process arguments.
- [x] Owner password is hashed with Argon2id.
- [x] Opaque sessions are stored as token digests and expire after 12 hours.
- [x] Logout revokes the current session; password rotation revokes all sessions.
- [x] Cookie-authenticated state-changing requests require a CSRF token.
- [x] Persistent login throttling (five failed attempts per owner/source-IP bucket in 15 minutes trigger a 15-minute lockout).\n- [ ] Password recovery, MFA, session inspection UI, and multi-user workspace isolation.
- [ ] Private data is excluded from sharing by default.

## Knowledge
- [ ] Search results identify source objects.
- [ ] Answers cite workspace sources when used.
- [ ] Conflicting sources coexist.
- [ ] Unknown facts are not silently invented.

## Memory and portability
- [x] Consistent SQLite snapshots are created without overwriting existing files.
- [x] Backup verification checks SQLite integrity and validates every stored record.
- [x] Restore validates the source, creates a pre-restore safety snapshot, stages a replacement, and swaps atomically.
- [ ] Automated restore testing on supported operating systems and crash-recovery testing.
- [x] Versioned portable workspace JSON export/import is implemented with integrity validation, staged replacement, pre-import safety backup, and owner credential exclusion (schema 1.3.0; legacy 1.0.0–1.2.0 imports supported).
- [ ] Clean-machine restore, import and crash-recovery validation across supported operating systems.

## AI provider and agents
- [ ] Replaceable provider adapter and sensitive-data controls.
- [ ] Explicit scoped agent permissions; no self-escalation.
- [ ] External side effects require approval and are auditable.

## Quality and release
- [x] CI runs lint, tests, Python dependency vulnerability audit, wheel/sdist builds, archive-content checks, and an installed-wheel HTTP smoke test.
- [ ] Secret scanning is enabled and passes.
- [ ] Production backup scheduling, encryption-at-rest policy, retention, and off-device recovery.
- [ ] Accessibility review and independent security review.
- [x] Operator acceptance runbook and evidence template documented ([Operator Acceptance](../docs/OPERATOR_ACCEPTANCE.md)).\n- [ ] Full user documentation complete.

A checkbox without evidence is not acceptance. CI evidence is recorded in GitHub Actions.

## Explicit memory lifecycle

- [x] Memory proposals are separate from durable memory and remain pending until an explicit owner approval request.
- [x] Rejection, approval, archive and restore actions are recorded in append-only lifecycle events.
- [x] Approved memory preserves optional document/chunk provenance.
- [x] Workspace export/import schema 1.3.0 includes memory proposals, approved items, lifecycle events, and Agent Runtime run/event audit records with integrity and linkage checks; legacy schemas 1.0.0–1.2.0 remain importable.
- [ ] Responsive memory review and correction UI; multi-user approval roles; deletion and retention controls.
