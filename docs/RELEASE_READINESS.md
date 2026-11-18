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

The integrated HUMANITY ONE 0.1 candidate is tracked in draft PR #26. CI run [43970440846](https://github.com/JoTalbot/humanity-os/actions/runs/43970440846) passed all 10 quality jobs/steps on the documentation update, including Ruff, pytest, pip-audit, wheel/sdist builds, archive verification, and a fresh-virtualenv installed-app smoke test. The automatic CI run [43970528285](https://github.com/JoTalbot/humanity-os/actions/runs/43970528285) also completed successfully on the latest integration head `a55861673e5fea8e3ff8a7a20bcfdfa26700e447`. The fresh-venv smoke verifies the installed CLI, packaged app import, and workspace plus static-asset routes through a loopback peer; it is not a clean-machine owner setup, backup/restore, cross-platform or production validation. CI runs for `integration/**`. The PR has not been merged into `main`, and no release is declared. The integration-branch reconciliation review is recorded in `docs/INTEGRATION_PLAN_HUMANITY_ONE_0.1.md`.

### Integration and verification
- [ ] Complete independent review of integration PR #26 and confirm every originating feature change is represented; preserve the source PRs until review is complete.
- [ ] Re-run full CI and end-to-end acceptance against the resulting \`main\` branch.
- [ ] Verify fresh install, password setup, local startup, backup, restore and portable import on a clean machine.
- [x] CI builds and inspects wheel/sdist contents, including the CLI entry point and static UI assets (run [43948575859](https://github.com/JoTalbot/humanity-os/actions/runs/43948575859)).
- [x] CI installs the built wheel and declared runtime dependencies into a fresh virtual environment, exercises the installed CLI, imports the packaged app, and verifies workspace plus static-asset HTTP routes over loopback (run [43970440846](https://github.com/JoTalbot/humanity-os/actions/runs/43970440846)).
- [ ] Validate owner-password setup, service startup, backup, restore and portable import on a clean machine and supported operating systems.
- [ ] Select a versioning and release artifact/signing policy.

### Security and privacy

Use [`docs/SECURITY_REVIEW_CHECKLIST.md`](SECURITY_REVIEW_CHECKLIST.md) as the evidence-based review record. It is a review plan only; no independent security review has yet been completed.
- [ ] Independent security review and penetration test of authentication, CSRF, session lifecycle, loopback enforcement, export/import and browser UI.
- [x] Integrate Agent Runtime lease ownership, heartbeat renewal, concurrent expiry recovery, stale-worker fencing, lease-fenced memory proposal writes, and accurate agent audit attribution (PR #29; CI [44278196403](https://github.com/JoTalbot/humanity-os/actions/runs/44278196403): 144 tests, Ruff, pip-audit, wheel/sdist verification, and clean-venv smoke test passed).
- [ ] Complete independent security review of the lease integration and verify SQLite locking, heartbeat failure, clock-step behavior, import/export recovery, and stale-worker fencing. Keep production single-process until this review and final integration review are complete.
- [ ] Verify lease-guarded memory proposal transactions and accurate agent actor attribution in the integrated candidate.
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

Do not tag, publish, deploy, expose to a LAN/public network, activate a remote provider, or merge stacked PRs solely because feature-branch CI passes. Each requires its own review and explicit release authorization.
