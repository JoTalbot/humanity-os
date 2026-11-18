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


## Reconciliation status — 2026-11-18 (current)

- Active candidate: PR #29, open Draft, head `fe5cca73ac068a4a86ed8e9c4d74c321fd15e373`, based on `integration/humanity-one-0.1`.
- Live comparison: 40 commits ahead / 0 behind the integration base; 451 ahead / 1 behind `main`. Histories remain divergent; merge base is `de57a48d8d57c023d02ee1c337e29bb557451a9a`. No merge or history rewrite has been performed.
- Latest automatic CI run for this exact head is [44281745359](https://github.com/JoTalbot/humanity-os/actions/runs/44281745359), in progress at the time of this snapshot. The preceding head's [44281451823](https://github.com/JoTalbot/humanity-os/actions/runs/44281451823) passed all 10 quality steps but does not validate the current head.
- The single main-only commit (`ac46e16728382c0af800421978f0bf7df6943de9`) adds `tests/test_memory.py`; the integration candidate contains an expanded 10-test implementation versus 7 tests on `main`. This is a content-level supersession assessment only, not completed Git-history reconciliation.
- PR #28 remains a historical source/reference, not a separate merge candidate. PR #26 remains the integration-foundation reference.
- Independent security review, external audit and penetration testing are canceled/not required. Project-owned regression, authorization, dependency and operational checks remain in scope.
- No merge, release, deployment, external integration or production operation was performed.

### Remaining release blockers, ordered

1. **Stacked history:** settle the 451/1 divergence and preserve source PR provenance and the main-only commit; no blind merge or ref rewrite.
2. **Authentication boundary (issue #2):** project-owned regression coverage for no owner/no token, configured owner/token, direct ASGI startup and unsupported network exposure; explicit safe first-run owner setup.
3. **Portability and deletion (issue #4):** versioned complete workspace export, secret exclusion, owner-confirmed full deletion, retention/backup disposal rules and verifiable round-trip/deletion behavior.
4. **Operator acceptance:** clean-machine setup, startup, backup, restore and portable import on supported operating systems.
5. **Privacy and recovery:** encryption-at-rest/export decision, key recovery, privacy disclosures/legal basis, retention expiry and backup disposal.
6. **Release engineering:** versioning, artifact provenance/signing, vulnerability disclosure and security update process.
7. **Governance:** license, contribution rules, ownership/representation and open constitutional decisions.
8. **Product quality:** accessibility evaluation and desktop/mobile workflow acceptance.

The above do not add an independent security review or external audit as a gate. Do not merge, tag, publish, deploy, expose to LAN/public network or activate a remote provider without separate explicit owner authorization.
