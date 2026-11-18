# HUMANITY OS Release Readiness

## Current state

**Not release-ready.** The project has a useful local HUMANITY ONE prototype, but its stacked implementation PRs have not been merged into \`main\`. Passing CI on feature branches is not the same as an integrated release.

## Implemented prototype capabilities

- Fail-closed authentication boundary and loopback-only ASGI peer enforcement.
- Local SQLite personal knowledge records, evidence/decision structures and portable export/import.
- Portable workspace schema 1.3.0 with document, explicit memory, and agent audit records; imports from schemas 1.0.0–1.2.0 remain supported.
- Local UTF-8 TXT/Markdown ingestion, source-preserving chunks, lexical search and bounded source-cited context packets.
- Explicit memory proposal, owner approval/rejection, archive/restore and append-only lifecycle events.
- Responsive local browser interface for notes, documents, memory review, and manually invoked allowlisted agent tools.
- Provider-neutral model gateway and source-grounded answer orchestration with per-request provider-processing consent.
- Citation validation verifies provenance only; it does not establish semantic support or factual truth.
- Constrained Agent Runtime with static allowlists, one-tool owner invocation, bounded inputs/outputs, minimal append-only audit, and pending-review-only memory proposals.
- No model provider, network integration or production deployment is enabled by default.

## Required before a public 0.1 release

The integrated HUMANITY ONE 0.1 candidate is tracked in Draft PR #29, based on `integration/humanity-one-0.1`; PR #26 is the integration-foundation reference and PR #28 is the original lease implementation/reference. Latest inspected CI run [44280523557](https://github.com/JoTalbot/humanity-os/actions/runs/44280523557) completed successfully with all 10 quality steps: Ruff, pytest, pip-audit, wheel/sdist builds, distribution-content verification, and clean-virtualenv installed-app/HTTP smoke checks. New CLI regression tests cover backup creation, backup verification, restore, and preservation of the pre-restore safety snapshot. The smoke verifies the installed CLI, packaged app import, and workspace plus static-asset routes through a loopback peer; it is not clean-machine owner setup, backup/restore, cross-platform or production validation. One existing Starlette TestClient deprecation warning remains. PR #29 has not been merged into `main`, and no release is declared. Current branch topology and stack-reconciliation notes are recorded in `docs/INTEGRATION_PLAN_HUMANITY_ONE_0.1.md`. As of 2026-11-18, PR #29 is 36 commits ahead / 0 behind its integration base and 447 ahead / 1 behind `main`; the histories are divergent. The sole main-only commit adds a memory-test file whose path is already present in the integration candidate with a different expanded 10-test implementation (versus 7 tests on `main`). This is a content-level equivalence assessment, not a completed history reconciliation.

### Integration and verification
- [ ] Complete internal reconciliation of integration PR #26 and confirm every originating feature change is represented; preserve source PRs as historical references.
- [ ] Re-run full CI and end-to-end acceptance against the resulting \`main\` branch.
- [ ] Verify fresh install, password setup, local startup, backup, restore and portable import on a clean machine.
- [x] Automated CLI regression coverage for backup creation/verification and restore with a verified pre-restore safety backup (CI [44279992873](https://github.com/JoTalbot/humanity-os/actions/runs/44279992873)); this does not replace clean-machine operator acceptance.
- [x] CI builds and inspects wheel/sdist contents, including the CLI entry point and static UI assets (run [43948575859](https://github.com/JoTalbot/humanity-os/actions/runs/43948575859)).
- [x] CI installs the built wheel and declared runtime dependencies into a fresh virtual environment, exercises the installed CLI, imports the packaged app, and verifies workspace plus static-asset HTTP routes over loopback (run [43970440846](https://github.com/JoTalbot/humanity-os/actions/runs/43970440846)).
- [ ] Validate owner-password setup, service startup, backup, restore and portable import on a clean machine and supported operating systems; current CI coverage is automated CLI-level regression, not cross-platform operational acceptance.
- [ ] Select a versioning and release artifact/signing policy.

### Security and privacy

Use [`docs/SECURITY_REVIEW_CHECKLIST.md`](SECURITY_REVIEW_CHECKLIST.md) as the project-owned internal security and release validation record. Independent security review, external audit, and penetration testing are not release requirements.
- [ ] Internal security checks for authentication, CSRF, session lifecycle, loopback enforcement, export/import and browser UI are covered by code inspection and automated regression tests.
- [x] Integrate Agent Runtime lease ownership, heartbeat renewal, concurrent expiry recovery, stale-worker fencing, lease-fenced memory proposal writes, and accurate agent audit attribution (PR #29; CI [44278196403](https://github.com/JoTalbot/humanity-os/actions/runs/44278196403): 144 tests, Ruff, pip-audit, wheel/sdist verification, and clean-venv smoke test passed).
- [x] Verify lease integration behavior through project-owned regression tests and CI: SQLite locking, heartbeat/lease renewal, expiry recovery, imported-run recovery, and stale-worker fencing. CI run [44279234278](https://github.com/JoTalbot/humanity-os/actions/runs/44279234278) passed 144 tests. Clock-step behavior remains a documented operational limitation, not a simulated guarantee. Retain the same-host/local-SQLite boundary; multi-host and network-filesystem coordination are unsupported.
- [x] Verify lease-guarded memory proposal transactions and accurate agent actor attribution in the integrated candidate; covered by PR #29 regression tests and CI run [44279234278](https://github.com/JoTalbot/humanity-os/actions/runs/44279234278).
- [ ] Define document and memory deletion, retention expiry and backup disposal workflows.
- [ ] Review privacy disclosures and legal basis for personal data processing.
- [ ] Decide encryption-at-rest, encrypted export and key recovery policy.
- [ ] Review dependency and supply-chain policy, SBOM and release provenance.
- [ ] Decide incident response, vulnerability disclosure and security update process.

### Product quality and governance
- [ ] Formal accessibility audit against a selected WCAG target; current UI is not certified.
- [ ] Validate core workflows manually on supported desktop and mobile browsers.
- [ ] Decide license, governance, contribution rules and ownership/representation model.
- [ ] Resolve open constitutional, identity, federation, retention, funding and agent-policy decisions.
- [ ] Add user-facing data export, deletion and recovery guidance.

### Deferred capabilities
- [ ] PDF/DOCX parsers, OCR, parser isolation and malformed-file testing.
- [ ] Semantic retrieval and answer-quality/semantic-entailment evaluation.
- [ ] Provider-specific adapters with provider locality/data residency disclosure and separate approval.
- [ ] Agent Runtime expansion, OS-level sandboxing and human approval for consequential actions; current runtime is constrained and one-tool-per-owner-request, not OS-sandboxed.
- [ ] Multi-user access, federation and collaboration.
- [ ] Full responsive workspace, account/session management and memory correction UX.

## Release rule

Do not tag, publish, deploy, expose to a LAN/public network, activate a remote provider, or merge stacked PRs solely because feature-branch CI passes. The active candidate is PR #29; PR #28 is an original implementation/reference branch and must not be merged independently. Each release action requires explicit owner authorization and a reconciled history against `main`.


## Current release status — 2026-11-18

- Active candidate: PR #29, open Draft, head `03d34e577f52ee55eeeda3a72f29bf9c88819d95`.
- CI [44281853101](https://github.com/JoTalbot/humanity-os/actions/runs/44281853101) passed all 10 quality steps on this exact head.
- Branch comparison: 42 ahead / 0 behind `integration/humanity-one-0.1`; 453 ahead / 1 behind `main`. Histories diverge; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- Authentication and workspace portability/deletion implementations and regression coverage are present. Relevant docs: `LOCAL_DEVELOPMENT.md`, `PRIVACY_MODEL.md`, `DATA_RETENTION.md`.
- PR #26/#28 remain historical provenance references. PR #29 is the sole integrated feature candidate.
- No merge, release, deployment or production operation was performed.

### Remaining release blockers

1. Reconcile the stacked Git history without losing the main-only memory-test change or source PR provenance.
2. Complete clean-machine owner setup, startup, backup, restore and portable import acceptance.
3. Decide encryption/key recovery, privacy/legal disclosures, retention expiry and backup disposal.
4. Finalize release provenance/signing, license, governance and contribution rules.
5. Complete accessibility evaluation and supported desktop/mobile acceptance.

Do not merge, tag, publish or deploy until the history and operator acceptance gates are resolved and the owner explicitly authorizes the action.
