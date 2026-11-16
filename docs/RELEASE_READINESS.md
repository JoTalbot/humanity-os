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

The integrated HUMANITY ONE 0.1 candidate is tracked in draft PR #26. Latest verified automatic GitHub Actions CI run [43969330683](https://github.com/JoTalbot/humanity-os/actions/runs/43969330683) passed on commit `be0ae8118c236e83eb9e62626c1e4570bd4671be`: Ruff, pytest, pip-audit, wheel and sdist builds, archive inspection, and isolated-target wheel installation with an HTTP smoke test for the workspace root and packaged JS/CSS assets. CI now also runs for `integration/**`. Later documentation commits are pending their own automatic CI. The PR has not been merged into `main`, and no release is declared. The integration-branch reconciliation review is recorded in `docs/INTEGRATION_PLAN_HUMANITY_ONE_0.1.md`.

### Integration and verification
- [ ] Complete independent review of integration PR #26 and confirm every originating feature change is represented; preserve the source PRs until review is complete.
- [ ] Re-run full CI and end-to-end acceptance against the resulting \`main\` branch.
- [ ] Verify fresh install, password setup, local startup, backup, restore and portable import on a clean machine.
- [x] CI builds and inspects wheel/sdist contents, including the CLI entry point and static UI assets (run [43948575859](https://github.com/JoTalbot/humanity-os/actions/runs/43948575859)).
- [x] CI installs the built wheel into an isolated target and verifies the installed app serves the workspace and static assets over loopback (run [43969330683](https://github.com/JoTalbot/humanity-os/actions/runs/43969330683)).
- [ ] Validate owner-password setup, service startup, backup, restore and portable import on a clean machine and supported operating systems.
- [ ] Select a versioning and release artifact/signing policy.

### Security and privacy
- [ ] Independent security review and penetration test of authentication, CSRF, session lifecycle, loopback enforcement, export/import and browser UI.
- [x] Implement Agent Runtime lease ownership, heartbeat renewal, concurrent expiry recovery, stale-worker fencing, and document the single-host/local-SQLite limitation (stacked PR #28; code CI [43947884587](https://github.com/JoTalbot/humanity-os/actions/runs/43947884587), 142 tests passed, Ruff and pip-audit passed).
- [ ] Complete independent security review of PR #28, including SQLite locking behavior, heartbeat failure handling, clock-step behavior, import/export recovery, and stale-worker fencing. Keep production single-process until this review and final integration review are complete.
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
