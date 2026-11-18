# HUMANITY ONE 0.1 — Release Readiness

## Release decision

**Status: NOT READY FOR PUBLIC RELEASE.**

PR #29 is the single integrated Draft candidate. Its current head passed the complete automated CI suite, including the packaged-app smoke test. This is strong candidate validation, not proof of clean-machine operation or authorization to publish.

## Implemented in the candidate

- Local SQLite workspace for knowledge, evidence, claims, decisions, revisions and provenance.
- Fail-closed single-owner authentication: Argon2id password hashing, opaque expiring sessions, CSRF protection, persistent login throttling and loopback-only ASGI enforcement.
- Bounded UTF-8 text/Markdown ingestion, chunk provenance, lexical search and source-grounded context.
- Citation provenance validation against local source manifests. This does not establish semantic support or factual truth.
- Explicit memory lifecycle with pending proposals, separate owner approval/rejection, archive/restore and append-only lifecycle events.
- Provider-neutral Model Gateway contract. No remote provider is enabled by default; provider processing is not part of the default local workflow.
- Constrained Agent Runtime with static tool allowlists, bounded inputs/results, one tool per explicit owner invocation, lease ownership/fencing, atomic completion/audit writes and pending-review-only memory proposals.
- Portable workspace export/import schema 1.3.0, integrity metadata, credential/session exclusion, staged validation and pre-import safety backup.
- SQLite backup verification and restore with a verified pre-restore safety backup.
- Offline confirmed workspace deletion with verified safety backup and SQLite WAL/SHM handling. This is not cryptographic erasure.
- Wheel/sdist packaging checks and clean-virtual-environment installed-app HTTP smoke test.
- Operator runbook and evidence template: [OPERATOR_ACCEPTANCE.md](OPERATOR_ACCEPTANCE.md).

## Latest automated validation

- Current PR head: `17a2258842921c74126113141fdcea8ce90be839`.
- GitHub Actions [run 44284661349](https://github.com/JoTalbot/humanity-os/actions/runs/44284661349) completed successfully on this exact head.
- All 10 quality steps passed: setup, dependency installation, Ruff lint, pytest, dependency vulnerability audit, wheel/sdist build, distribution-content verification, and clean-virtual-environment packaged-app HTTP smoke test.
- The test step passed; the current run's job summary does not expose a test-count value. The immediately preceding code-head run 44284176087 reported 147 passing tests.
- No manual test suite or workflow dispatch was started for this documentation update.
- CI does not prove clean-machine owner setup, supported-OS operation, real backup/restore/import acceptance, accessibility, legal readiness or production readiness.

## Candidate and branch topology

- Active candidate: [PR #29](https://github.com/JoTalbot/humanity-os/pull/29), open Draft, branch `fix/agent-lease-side-effects-audit`, base `integration/humanity-one-0.1`.
- PR #26 remains the integration-foundation reference. PR #28 remains the original lease implementation/reference. PR #29 contains the integrated and hardened lease implementation; do not merge PR #28 independently.
- Latest live comparison recorded for the candidate against `main`: 470 commits ahead, 1 behind; histories are divergent. The comparison against `integration/humanity-one-0.1` was 59 ahead, 0 behind before the latest documentation-only commits. Recheck live counts before any integration operation.
- `main` contains one earlier memory-test commit absent from the integration ancestry. Its relevant test intent is represented in the candidate's expanded tests, including append-only deletion protection and archived-memory export/import lifecycle coverage. This is content-level coverage, not Git ancestry reconciliation.
- No merge, rebase, cherry-pick, force-push, ref rewrite, tag, publication or deployment has been performed.

## Mandatory release gates

### A. Git integration and provenance
- [ ] Select a history-reconciliation strategy that preserves the main-only memory-test intent and source PR provenance.
- [ ] Review the complete resulting diff against `main`, including deletions, migrations and workflow changes.
- [ ] Re-run the full CI suite on the reconciled candidate.
- [ ] After separately authorized integration, verify the target branch and resulting commit.
- [ ] Keep PR #26 and #28 as provenance references; do not independently merge the superseded lease implementation.

### B. Clean-machine operator acceptance
- [ ] Execute [OPERATOR_ACCEPTANCE.md](OPERATOR_ACCEPTANCE.md) on a genuinely clean, disposable supported machine.
- [ ] Record OS/version, architecture, Python version, exact commit/artifact SHA-256 and operator/date.
- [ ] Verify owner-password setup, login/logout, rejected credentials and loopback-only access.
- [ ] Verify note/document ingestion, search and source provenance.
- [ ] Verify pending memory proposal, explicit approval, archive state and lifecycle history.
- [ ] Verify SQLite backup, integrity check, restore and retained pre-restore safety backup.
- [ ] Verify portable export/import into a second isolated workspace and configure a new owner password.
- [ ] Preserve non-secret evidence and record failures, recovery steps and downtime.
- [ ] Repeat for every OS/browser combination claimed as supported. Until then, publish no broader compatibility claim.

### C. Privacy, retention and recovery decisions
- [ ] Owner selects encryption-at-rest and encrypted-export policy, including key recovery/loss behavior.
- [ ] Qualified review establishes intended jurisdiction, privacy disclosures and legal basis.
- [ ] Owner approves retention periods, backup inventory, disposal workflow and operational responsibility.
- [ ] Document incident response, vulnerability reporting and security-update process.
- [ ] Decide SBOM, artifact provenance and signing requirements.
- [ ] Do not represent recommendations in `DATA_RETENTION.md` as enforced application behavior.

### D. Product, accessibility and governance
- [ ] Select code and documentation licenses after IP/legal review; public visibility does not grant reuse rights. See [LICENSE-DECISION.md](../LICENSE-DECISION.md).
- [ ] Ratify governance, contribution, decision-making, dispute and stewardship rules or explicitly scope them as post-0.1 work.
- [ ] Select an accessibility target and record an evaluation.
- [ ] Complete desktop/mobile browser acceptance for the explicitly supported matrix.
- [ ] Complete user-facing installation, upgrade, rollback, export, restore and deletion guidance.
- [ ] Resolve or explicitly defer legal stewardship. “Owned by humanity” is a mission, not an established legal status.

## Explicit 0.1 limitations

- Single local owner; no multi-user isolation, federation or collaboration.
- SQLite coordination is limited to same-host processes sharing a local filesystem with reliable SQLite locking. Multi-host and network-filesystem coordination are unsupported.
- Loopback-only by default; no LAN/public exposure or remote provider is enabled by default.
- Ingestion is bounded to UTF-8 text and Markdown; PDF/DOCX/OCR and parser isolation are deferred.
- Lexical retrieval is implemented; semantic retrieval and rigorous answer-quality evaluation are deferred.
- Citation validation checks provenance, not entailment or truth.
- Memory archive is not erasure; full memory deletion and automatic retention expiry are not implemented.
- Workspace deletion does not erase exports, backups, snapshots, host logs or storage-media remnants.
- Agent Runtime is constrained but is not an OS-level sandbox or autonomous agent platform.

## Release rule

Do not mark HUMANITY ONE 0.1 release-ready until every mandatory gate is either completed with evidence or explicitly re-scoped by the owner with a documented release limitation. Do not merge, tag, publish, deploy, expose beyond loopback or activate a remote provider without separate explicit authorization.
