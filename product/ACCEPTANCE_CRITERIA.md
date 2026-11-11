# HUMANITY ONE 0.1 — Acceptance Criteria

## Installation
- [ ] Clean local deployment works from documented instructions.
- [ ] No committed secrets.
- [ ] Upgrade and rollback are documented.

## Identity and privacy
- [ ] Server-side workspace isolation.
- [ ] Sessions are inspectable and revocable.
- [ ] Private data is excluded from sharing by default.

## Knowledge
- [ ] Add, inspect, edit and delete documents/notes.
- [ ] Search results identify source objects.
- [ ] Answers cite workspace sources when used.
- [ ] Conflicting sources coexist.
- [ ] Unknown facts are not silently invented.

## Memory
- [ ] Saving is explicit.
- [ ] User can inspect, correct, export and delete memory.
- [ ] Retention and backup implications are documented.

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
- [ ] Automated checks pass with recorded evidence.
- [ ] Dependency and secret scans pass.
- [ ] Backup restore and export/import are demonstrated.
- [ ] Accessibility review is completed.
- [ ] Independent security review is completed or residual risks are public.
- [ ] User docs and operator runbook are published.

A checkbox without evidence is not acceptance.
