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
- [ ] Password recovery, MFA, login throttling, session inspection UI, and multi-user workspace isolation.
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
- [ ] Full export/import portability; JSON export exists, import is not implemented.

## AI provider and agents
- [ ] Replaceable provider adapter and sensitive-data controls.
- [ ] Explicit scoped agent permissions; no self-escalation.
- [ ] External side effects require approval and are auditable.

## Quality and release
- [x] CI runs lint, tests, and Python dependency vulnerability audit.
- [ ] Secret scanning is enabled and passes.
- [ ] Production backup scheduling, encryption-at-rest policy, retention, and off-device recovery.
- [ ] Accessibility review and independent security review.
- [ ] Operator runbook and user documentation complete.

A checkbox without evidence is not acceptance. CI evidence is recorded in GitHub Actions.
