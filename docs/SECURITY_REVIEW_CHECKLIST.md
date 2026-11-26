# HUMANITY OS Internal Security and Release Validation Checklist

Status: **internal validation record**. This checklist is used by the project maintainer to track code-level controls, automated tests, operational evidence, and release decisions. No independent security review, external audit, or penetration test is required or planned as a release gate. This record is not a security attestation.

## Review record

- Maintainer / operator:
- Review date:
- Reviewed integration commit:
- Reviewed Agent Runtime PR #28 head:
- Environment and operating system:
- Toolchain / resolved dependency versions:
- Overall result: Not assessed / Pass / Pass with conditions / Fail
- Findings and tracking references:

For each applicable item record **Pass**, **Fail**, **Not assessed**, or **Not applicable**, with evidence. A checked box without reproducible evidence is not a pass. Evidence may come from source inspection, project-owned regression tests, CI, and documented operational checks.

## 1. Authentication, sessions and request boundaries

- [ ] Verify password setup and storage use an appropriate password-hashing scheme; confirm no plaintext or reversible password storage.
- [ ] Verify login, logout, session rotation, expiration, cookie flags, and invalid-session behavior.
- [ ] Verify every state-changing route enforces CSRF protection and rejects missing, invalid, and cross-origin tokens.
- [ ] Verify unauthenticated requests cannot read workspace data, agent history, exports, or protected application routes.
- [ ] Verify authorization is enforced server-side and does not rely on UI visibility or client-supplied ownership.
- [ ] Verify errors do not disclose credentials, session identifiers, local paths, SQL details, or sensitive record contents.
- [ ] Verify rate limits or documented compensating controls for password guessing and expensive operations.

**Evidence required:** route-by-route test results, relevant code references, and representative rejected-request traces.

## 2. Loopback and deployment trust boundary

- [ ] Verify the loopback-only peer check uses the actual ASGI connection peer and cannot be bypassed by untrusted forwarding headers.
- [ ] Verify X-Forwarded-For, Forwarded, Host, and proxy-related headers cannot turn an untrusted remote peer into a trusted loopback peer.
- [ ] Verify the server binds only to the intended interface by default.
- [ ] Verify documentation does not imply loopback protection is a network firewall or substitute for deployment controls.
- [ ] Verify LAN/public exposure is blocked by default or requires a separately reviewed deployment design.

**Evidence required:** IPv4/IPv6 loopback and non-loopback tests, spoofed forwarding-header tests, and actual bind configuration.

## 3. Agent Runtime capability limits

- [ ] Verify tool names are selected only from the static allowlist and cannot be replaced by caller-controlled module/function names.
- [ ] Verify one tool invocation per explicit owner request; no autonomous loop, recursive tool chain, or hidden follow-up invocation.
- [ ] Verify input and result size limits are enforced server-side before persistence or rendering.
- [ ] Verify there is no shell, arbitrary Python execution, unrestricted filesystem access, unrestricted network access, or implicit tool discovery.
- [ ] Verify memory proposals remain pending review and cannot silently become approved memory.
- [ ] Verify audit records are append-only at the application boundary and contain only minimum required data.
- [ ] Verify tool errors and timeouts leave runs recoverable without leaking secrets or partial sensitive output.

**Evidence required:** adversarial tests for allowlist bypass, oversized payloads, repeated calls, unauthorized memory promotion, and audit mutation.

## 4. Agent Runtime leases and SQLite concurrency (PR #28)

- [ ] Verify worker identity is unique per store/process and forked children rotate inherited identity before performing work.
- [ ] Verify heartbeat renewal continues during long-running tool calls and stops when the invocation exits.
- [ ] Verify an expired lease cannot be renewed or completed by its former owner.
- [ ] Verify stale workers are fenced from appending terminal events after a replacement worker recovers the run.
- [ ] Verify concurrent recovery across independent processes produces exactly one interrupted terminal transition.
- [ ] Verify BEGIN IMMEDIATE and conditional updates provide intended atomicity under the supported local SQLite/filesystem configuration.
- [ ] Verify behavior when heartbeat renewal fails, a process is killed, the database is busy, or a transaction is interrupted.
- [ ] Verify lease migration for every supported legacy database shape, including partially migrated or malformed metadata.
- [ ] Verify portable export excludes live worker/lease ownership and imported running records are safely recovered.
- [ ] Verify forward/backward wall-clock jumps, clock skew, and host time synchronization assumptions.
- [ ] Verify upgrade procedure stops all app processes and does not permit mixed old/new workers.

**Supported boundary to validate:** same-host processes sharing one local SQLite database on a filesystem with reliable SQLite locking. No multi-host, distributed, or network-filesystem guarantee is claimed.

**Evidence required:** process-level concurrency tests, migration fixtures, crash/restart tests, clock-control tests, and documented operator observations. Unit tests alone do not prove filesystem or production behavior.

## 5. Workspace data, export/import and privacy

- [ ] Verify path handling prevents traversal, symlink escape, unexpected file reads, and writes outside the workspace.
- [ ] Verify import rejects malformed archives, traversal entries, duplicate/conflicting records, oversized files, and unsupported schema versions safely.
- [ ] Verify export is complete and excludes credentials, session data, live lease ownership, and unintended machine metadata.
- [ ] Verify backup/restore behavior, including interrupted writes and restoration into a fresh workspace.
- [ ] Verify deletion, retention, archive/restore, and backup disposal semantics are accurately documented.
- [ ] Verify sensitive document content is not copied into logs or audit records unnecessarily.
- [ ] Verify user consent is explicit and scoped before any external provider receives content.

**Evidence required:** malicious archive fixtures, path-boundary tests, backup/restore results, and data-flow review.

## 6. Citation and knowledge integrity

- [ ] Verify citation identifiers and source offsets are validated against the actual stored source manifest.
- [ ] Verify stale, missing, altered, or mismatched sources fail closed.
- [ ] Verify UI and API distinguish provenance validation from semantic support and factual truth.
- [ ] Verify claim/evidence relationships preserve source identity and revision history.
- [ ] Verify conflicts and uncertainty are represented rather than silently collapsed into a single asserted fact.

**Evidence required:** tampering tests, source-revision tests, and API/UI assertions that provenance is not described as truth verification.

## 7. Model gateway and external processing

- [ ] Verify no provider is activated by default and no content is transmitted without per-request consent.
- [ ] Verify provider configuration cannot be injected through untrusted workspace content.
- [ ] Verify timeouts, retries, response-size limits, and provider errors do not trigger unintended repeated disclosure.
- [ ] Verify logs and telemetry do not retain prompts, documents, credentials, or provider responses beyond documented policy.
- [ ] Verify provider locality, retention, and data-residency claims are accurate for each enabled adapter.

**Evidence required:** outbound-request capture in a controlled test environment and consent-denial tests.

## 8. Dependencies, packaging and release integrity

- [ ] Review dependency vulnerability audit output and determine whether findings require action.
- [ ] Verify wheel and source archives contain only intended files and no secrets, local databases, test artifacts, or development credentials.
- [ ] Verify the installed wheel works in a clean environment with declared runtime dependencies.
- [ ] Verify supported Python/OS versions, install instructions, service lifecycle, backup, and restore on clean machines.
- [ ] Define artifact provenance, signing, versioning, and vulnerability-response procedures.

**Evidence required:** CI run links, archive inventory, clean-machine installation record, and dependency review.

## 9. Accessibility, governance and user safety

- [ ] Review keyboard navigation, focus order, labels, contrast, and screen-reader behavior against a selected WCAG target.
- [ ] Verify consequential actions are distinguished from previews and require explicit owner approval.
- [ ] Verify users can inspect, correct, export, and delete their data under documented rules.
- [ ] Verify governance, contribution, ownership, and dispute-resolution language does not overstate authority or consensus.

**Evidence required:** accessibility audit, owner-journey walkthrough, and approved governance decisions.

## 10. Release decision

- [ ] Internal security checklist items are assessed; critical/high findings are fixed and retested or explicitly accepted by the owner.
- [ ] All critical/high findings are fixed and retested; medium/low findings have owners and due dates.
- [ ] PR #26 complete stacked history and originating feature contracts have been reconciled.
- [ ] PR #28 base/head divergence has been safely reconciled and its final diff checked against the integration plan.
- [ ] Full CI and acceptance checks pass on the final candidate commit.
- [ ] Clean-machine install, password setup, backup, restore, and supported-platform checks pass.
- [ ] Privacy, accessibility, governance, versioning, and release artifact decisions are approved.
- [ ] Production topology and operational limits are explicitly approved.

Until the remaining release gates are satisfied, keep the candidate in Draft and do not tag, publish, deploy, expose it to a LAN/public network, or enable external providers. A green feature-branch CI run alone is not release authorization. No independent review or penetration test is part of this process; the project owner decides release authorization from the recorded internal evidence and accepted limitations.
