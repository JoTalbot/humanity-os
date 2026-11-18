# HUMANITY ONE 0.1 — Release Readiness

## Release decision

**Status: NOT READY FOR PUBLIC RELEASE.**

The current product is a single-owner, local-first prototype. PR #29 is the integrated candidate. A green feature-branch CI run is not a release: the Git history has not been reconciled with `main`, and clean-machine operator acceptance has not yet been executed.

## Implemented

- Local SQLite workspace with knowledge, evidence, claims, decisions, revisions and provenance.
- Fail-closed owner authentication, Argon2id password hashing, opaque expiring sessions, CSRF protection, login throttling and loopback-only ASGI enforcement.
- Local UTF-8 text/Markdown ingestion, chunk-level provenance, lexical search and bounded source-grounded context.
- Citation validation against the local source manifest. This verifies provenance, not semantic support or factual truth.
- Explicit memory lifecycle: pending proposals, owner approval/rejection, archive/restore and append-only lifecycle events.
- Provider-neutral Model Gateway contract. No provider is enabled by default; provider processing requires explicit per-request consent.
- Constrained Agent Runtime: static allowlist, bounded inputs/outputs, one tool per owner invocation, lease fencing, append-only minimal audit and pending-review-only memory proposals.
- Versioned portable workspace export/import schema 1.3.0, SHA-256 integrity metadata, secret exclusion, staged validation and pre-import safety backup.
- SQLite backup verification and restore with pre-restore safety backup.
- Offline confirmed workspace deletion with verified pre-deletion backup and WAL/SHM handling. This is not cryptographic erasure.
- Packaged wheel/sdist checks and clean-virtual-environment installed-app HTTP smoke test.
- Operator acceptance runbook and evidence template: [OPERATOR_ACCEPTANCE.md](OPERATOR_ACCEPTANCE.md).

## Latest automated validation

- Latest verified PR-head CI run [44284176087](https://github.com/JoTalbot/humanity-os/actions/runs/44284176087) completed successfully on candidate head `139793dbbaa5ed0000d29108e60a4c428516d6e1`. The PR description records all 10 quality steps passing, including Ruff, 147 pytest tests, dependency audit, wheel/sdist build, distribution verification and clean-venv packaged-app HTTP smoke test.
- 147 pytest tests passed.
- Ruff lint passed.
- Dependency vulnerability audit passed.
- Wheel and source distribution built and distribution contents verified.
- Built wheel installed into a clean virtual environment; packaged CLI, application import, workspace route and static asset route smoke checks passed.
- One Starlette TestClient deprecation warning remains.
- These checks do not prove clean-machine owner setup, supported-OS operation, backup/restore/import acceptance, accessibility, or production readiness.

## Current candidate and history

- Active candidate: [PR #29](https://github.com/JoTalbot/humanity-os/pull/29), open Draft, branch `fix/agent-lease-side-effects-audit`, base `integration/humanity-one-0.1`.
- PR #26 and #28 remain source/provenance references; PR #29 is the single integrated candidate.
- The candidate is ahead of its integration base and its history diverges from `main`.
- `main` contains one earlier memory-test commit not present in the integration ancestry. The relevant test intent has been carried into the candidate's expanded suite, including append-only deletion protection and archived-memory export/import lifecycle coverage. This is content-level reconciliation, not Git-history reconciliation.
- Do not merge, rebase, cherry-pick, force-push, rewrite refs, tag, publish or deploy as part of this readiness checklist. Any such action requires separate owner authorization.

See [INTEGRATION_PLAN_HUMANITY_ONE_0.1.md](INTEGRATION_PLAN_HUMANITY_ONE_0.1.md) for implementation and branch-provenance notes.

## Release blockers

### 1. Git integration
- [ ] Choose and execute a history-reconciliation strategy that preserves the main-only memory test intent and source PR provenance.
- [ ] Review the resulting diff against `main`.
- [ ] Run the full CI suite on the reconciled candidate and, after separately authorized integration, on the resulting target branch.

### 2. Operator acceptance
- [ ] Execute [OPERATOR_ACCEPTANCE.md](OPERATOR_ACCEPTANCE.md) on a genuinely clean supported machine.
- [ ] Verify owner-password setup, login/logout and loopback-only access.
- [ ] Verify knowledge/document ingestion and source provenance.
- [ ] Verify memory approval, archive state and lifecycle history.
- [ ] Verify SQLite backup, integrity check, restore and retained pre-restore backup.
- [ ] Verify portable export/import into a second isolated workspace, including new owner-password setup.
- [ ] Record OS, architecture, Python version, artifact hash, results, recovery observations and evidence location.
- [ ] Repeat on every operating system/browser combination that will be claimed as supported.

### 3. Privacy, retention and recovery
- [ ] Decide encryption-at-rest and encrypted-export policy, including key recovery and loss scenarios.
- [ ] Approve privacy disclosures, jurisdiction and legal basis for intended deployments.
- [ ] Define retention periods, backup inventory, disposal workflow and operator responsibilities.
- [ ] Document incident response, vulnerability reporting and security update process.
- [ ] Decide release SBOM, artifact provenance and signing policy.

### 4. Product and governance
- [ ] Select code and documentation licenses after IP review; public repository visibility does not grant reuse rights. See [LICENSE-DECISION.md](../LICENSE-DECISION.md).
- [ ] Finalize governance, contribution, decision-making and dispute-resolution rules. See [GOVERNANCE_MODEL_DRAFT.md](../governance/GOVERNANCE_MODEL_DRAFT.md).
- [ ] Select an accessibility target and evaluate the UI against it.
- [ ] Complete supported desktop and mobile browser acceptance.
- [ ] Complete user-facing installation, upgrade, rollback, export, restore and deletion documentation.
- [ ] Resolve the ownership/stewardship legal structure; “owned by humanity” remains a mission and governance objective, not a legal status.

## Explicit 0.1 limitations

- Single local owner; no multi-user isolation, federation or collaboration.
- Local SQLite coordination only. Agent leases are supported for same-host processes sharing a reliable-locking local SQLite filesystem; multi-host and network filesystems are unsupported.
- No remote access, LAN exposure, public hosting or external provider is enabled by default.
- Document ingestion is bounded to UTF-8 text and Markdown; PDF/DOCX/OCR and parser isolation are deferred.
- Lexical retrieval is implemented; semantic retrieval and rigorous answer-quality evaluation are deferred.
- Citation checks establish source provenance only, not whether a source semantically entails a claim.
- Memory archive is not erasure. The prototype does not provide full memory deletion or automatic retention expiry.
- Workspace deletion removes the active database and SQLite sidecars after a verified safety backup; exports, backups, snapshots, host logs and storage-media remnants remain outside that boundary.
- The current Agent Runtime is constrained but is not an OS-level sandbox.

## Release rule

Do not call HUMANITY ONE 0.1 release-ready until all mandatory blockers have evidence and are reviewed. Do not merge, tag, publish, deploy, expose the service beyond loopback, or activate a remote provider without separate explicit owner authorization.
