# HUMANITY ONE 0.1 — Acceptance Criteria

## Installation
- [ ] Clean local deployment works from documented instructions.
- [ ] No committed secrets.
- [ ] Upgrade and rollback are documented.

## Identity and privacy
- [ ] Server-side workspace isolation.
- [ ] Sessions are inspectable and revocable.
- [ ] Private data is excluded from sharing by default.
- [x] Optional single-secret bearer authentication protects API routes when configured.
- [x] Token generation uses the operating system cryptographic random source and emits a 256-bit token once.
- [ ] Individual user identities, scoped authorisation, and revocable sessions.

## Knowledge
- [ ] Add, inspect, edit and delete documents/notes.
- [ ] Search results identify source objects.
- [ ] Answers cite workspace sources when used.
- [ ] Conflicting sources coexist.
- [ ] Unknown facts are not silently invented.

## Memory
- [ ] Saving is explicit.
- [ ] User can inspect, correct, export and delete memory.
- [x] Retention and backup implications are documented for local snapshots and exports.
- [x] Consistent SQLite snapshots are created without overwriting existing files.
- [x] Backup verification checks SQLite integrity and validates every stored record.
- [x] Restore validates the source, creates a pre-restore safety snapshot, stages a replacement, and swaps atomically.
- [x] Restore is a local CLI operation requiring an explicit confirmation flag.
- [ ] Automated restore testing on supported operating systems and crash-recovery testing.

## AI provider
- [ ] Provider is behind a stable adapter.
- [ ] Provider failure does not corrupt user data.
- [ ] Provider can be changed without data migration.
- [ ] Sensitive-data handling is disclosed.

## Agents
- [ ] Tool permissions are explicit and scoped.
- [ ] No agent can grant itself capabilities.
- [ ] External side effects require approval.
- [ ] History distinguishes attempted from completed actions.

## Quality and release
- [x] CI runs lint and tests; current run 43083118549 passed.
- [x] CI includes a Python dependency vulnerability audit; current run 43083118549 passed after upgrading pytest and setuptools.
- [ ] Secret scanning is enabled and passes.
- [ ] Full export/import portability is demonstrated; JSON export exists, but import is not implemented.
- [ ] Production backup scheduling, encryption-at-rest policy, retention, and off-device recovery are implemented.
- [ ] Accessibility review is completed.
- [ ] Independent security review is completed or residual risks are public.
- [ ] User docs and operator runbook are published.

A checkbox without evidence is not acceptance.
