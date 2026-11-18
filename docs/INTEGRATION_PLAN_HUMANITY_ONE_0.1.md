# HUMANITY ONE 0.1 Integration Plan

## Authoritative current status — 2026-11-18

PR #29 is the sole integrated Draft candidate. The latest measured HEAD before this status note was `e6332b81ccdf66b8850cb1397fa219162b5451ed`: 177 commits ahead / 0 behind `integration/humanity-one-0.1`, and 588 ahead / 1 behind `main` (diverged; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`). No status checks are attached to that HEAD. The CI workflow is intentionally not triggered by feature-branch pushes; historical runs do not validate the current candidate.

Manual operator acceptance is DEFERRED by owner for the current development phase. Do not execute or schedule clean-machine setup or manual backup/restore/import walkthroughs. Keep those scenarios marked unvalidated, not passed; they are not current development gates. The runbook remains reference documentation. Independent security review is not required and is not a release gate.

Current work priorities:
1. Continue implementation and ordinary focused engineering review; do not launch broad tests during routine development.
2. Preserve source history while preparing an explicit reconciliation plan for the one main-only commit and the stacked PR history. Do not blindly merge, rebase, cherry-pick, force-push, or rewrite refs.
3. Keep automated milestone checks for changed critical invariants and reserve full CI for the exact release-candidate HEAD.
4. Resolve remaining owner policy decisions (privacy/key recovery, retention, licensing/governance, accessibility and supported-platform scope) before claiming public-release readiness.
5. Keep PR #29 Draft; no merge, release, publication or deployment is authorized by this plan.

Historical integration sequence and dated snapshots below are retained for provenance. Where they conflict with this authoritative status, this section and the latest owner decisions prevail.

---
Status: integrated HUMANITY ONE 0.1 Draft candidate in PR #29, based on `integration/humanity-one-0.1`; PR #26 remains the integration-foundation reference. PR #28 is the original Agent Runtime lease implementation/reference and must not be merged independently.
Base: `humanity-one/source-grounded-context` at `ba742e019dcdde2a51bd0bda41fc5ed85cd567ae`
Related work: PR #11, #13, #15, #17, #19, #21, #23, #25.

## Objective

Produce one reviewable HUMANITY ONE 0.1 release candidate without losing work from either active feature line. This document records the integration order and explicit blockers. It does not claim that the feature branches have been merged or that the release candidate is complete.

## Current branch topology

### Line A: workspace and agent runtime
- #11 Explicit Memory
- #13 Workspace UI
- #15 Source Context
- #17 Grounded Answers
- #19 E2E Acceptance
- #21 Agent Runtime

### Line B: grounded context and citation provenance
- #11 Explicit Memory
- #23 Source-Grounded Context
- #25 Citation Verification

The two lines are not currently a single linear history. PR #13 is based on an older Explicit Memory commit. PR #21 and PR #25 have diverged histories and must not be combined by blindly retargeting one PR onto the other.

## Integration baseline

Use `humanity-one/source-grounded-context` (PR #23 head) as the working baseline for the next integration stage because it is directly based on the current Explicit Memory head. Preserve the original PRs and their branches as immutable review references.

## Integrated in this candidate

- Workspace UI static assets and UI documentation/tests from #13, with server routing added to the current authenticated application.
- Bounded local source context and source-cited answer flow from #15/#17; provider processing remains disabled unless explicitly configured and separately consented per request.
- Citation provenance validation from #25, including manifest/source verification and an explicit `semantic_support_verified: false` result.
- Constrained Agent Runtime from #21: static researcher/curator allowlists, one tool per explicit request, bounded inputs/outputs, pending-review-only memory proposals, append-only minimal audit, and schema 1.3.0 export/import support.
- Agent audit event listing is bounded to 100 records, and run completion is guarded to allow one terminal transition.

## Historical integration milestone (completed work; retained for traceability)

- Ported the owner-journey acceptance test from #19 and updated its workspace export expectation to schema 1.3.0.
- Combined UI/context/agent contracts and preserved the original PRs as provenance references.
- The CI run recorded here belongs to historical head `5d077980032ec6b9e82605ab7b8e62a76d28059c`; it is not evidence for the current candidate.
- PR #29 is already the integrated Draft candidate; do not create a duplicate release-candidate PR.

## Required integration sequence

1. Reconfirm PR heads, base SHAs, and review state immediately before each integration operation.
2. Integrate Citation Verification (#25) into the source-grounded-context line, preserving its provenance-only guarantee:
   - source/citation provenance may be verified;
   - semantic support must remain explicitly unverified unless a separate semantic verifier is implemented.
3. Port Workspace UI (#13) onto the current baseline:
   - bring over the UI static assets, workspace documentation, and UI tests;
   - manually reconcile `src/humanity_os/app.py`, README, product spec, privacy and threat-model documentation;
   - retain newer Explicit Memory storage and export behavior;
   - do not force-push or rewrite the original PR branch.
4. Integrate Source Context / Grounded Answers (#15/#17) only after confirming their contracts are compatible with the source-grounded-context implementation. Avoid duplicate endpoints, models, or chunking paths.
5. Integrate Agent Runtime (#21) after the API and storage contracts are reconciled:
   - preserve the explicit owner-triggered, one-tool-per-call model;
   - preserve the tool allowlist and pending-review-only memory proposals;
   - do not add shell, arbitrary Python, unrestricted filesystem/network access, autonomous loops, or implicit approval.
6. Reconcile E2E acceptance (#19) with the final integrated journey and add coverage for the combined UI, source grounding, citation provenance, and agent permission boundaries.
7. Keep automatic PR CI green as changes land; use project-owned security checks and regression tests. Any manually initiated extended test campaign still requires separate authorization.
8. Prepare a release-candidate PR with a change inventory, migration/compatibility notes, security limitations, and test evidence.

## Known hardening items to track

- Agent Runtime: worker identity, expiring leases, heartbeat renewal and atomic stale-run recovery are ported from PR #28. PR #29 adds a SQLite write-locked transaction that atomically commits memory proposal creation, its audit event, and the run's completed state; it also records the initiating agent as the audit actor. Lease coordination is limited to same-host processes sharing local SQLite with reliable locking; multi-host and network-filesystem coordination are unsupported.
- Citation verification: strictly validate citation identifier syntax and source offsets; document whether citation counts mean unique IDs or occurrences.
- Workspace UI: revalidate authentication, CSRF, loopback restrictions, static asset routing, and behavior with the latest memory schema.
- Deployment: do not describe the current runtime as OS-sandboxed or fully autonomous.

## Safety and release boundaries

- No PR is merged by this plan.
- No production deployment, external integration, outbound message, or real-world action is authorized.
- CI workflows are exercised automatically by branch pushes and pull requests. The integration operator has not manually dispatched a workflow or run tests outside CI.
- Keep original feature PRs open until their changes are represented and reviewed in the integration PR.
- Release readiness requires explicit review of the final integrated diff and test results.

## Acceptance criteria

- One coherent branch contains the intended 0.1 feature set with no duplicated or silently dropped contracts.
- Existing security boundaries remain enforced.
- Source citations are described accurately as provenance-checked, not necessarily semantically supported.
- Agent capabilities and limitations are explicit and tested.
- Data export/import remains backward-compatible with documented schema versions.
- The full owner journey is covered by acceptance tests.
- A reviewer can trace every integrated feature to its originating PR.


## Reconciliation review — 2026-11-17

The earlier reconciliation notes below describe the initial integration state and are superseded where this section records later changes.

- PR #26 remains an open Draft integration candidate based on `humanity-one/source-grounded-context`; it has not been merged or retargeted.
- Historical comparison at the 2026-11-17 review: integration branch was reported 407 commits ahead and one behind `main`. This count is superseded by the 2026-11-18 comparison below; branch divergence is not a merge-readiness signal.
- The main-only memory test change remains superseded by the integration branch's schema-1.3.0 test coverage, which includes Agent Runtime audit tables and legacy schema 1.0.0–1.2.0 import compatibility.
- PR #28 now implements process ownership, expiring leases, daemon heartbeat renewal, owner fencing, fork-safe worker identity, and atomic stale-run recovery. Its code CI passed in run `43947884587`; the PR remains open and Draft. Its supported deployment boundary is same-host processes sharing a local SQLite database with reliable locking. No multi-host or network-filesystem guarantee is made.
- CI now includes `integration/**`, builds wheel and sdist archives, checks the CLI entry point and static assets, and installs the wheel into an isolated target for an HTTP smoke test. Run `43969330683` passed on commit `be0ae8118c236e83eb9e62626c1e4570bd4671be`; the test confirmed the installed app serves the workspace root and static assets through a loopback peer. The initial smoke harness failed because its default TestClient peer was non-loopback; the harness was corrected without weakening the product's loopback guard.
- Acceptance criteria and documentation now describe portable workspace schema 1.3.0 and imports from 1.0.0–1.2.0. Clean-machine owner setup, backup, restore and cross-platform recovery remain open.
- PR #26 and #28 have no submitted reviews or inline review threads as of this review.
- No PR was merged, no force-push was performed, no workflow was manually dispatched, and no release or deployment was made.
- Latest verification: CI run `43970440846` passed all 10 quality steps, including lint, tests, dependency audit, wheel/sdist inspection and fresh-virtualenv packaged-app smoke checks. Automatic CI run `43970528285` also completed successfully on integration head `a55861673e5fea8e3ff8a7a20bcfdfa26700e447`. No manual workflow dispatch or out-of-CI test run was performed.
- 2026-11-18 comparison of `fix/agent-lease-side-effects-audit` against `main`: 442 commits ahead and one behind; histories are divergent. This is a manual reconciliation gate, not a merge-readiness signal.
- PR #28's head remains `229cc91266b43452ec79f7e7f72e981344f025e5`; its recorded base SHA `9804c7c3df31608cf47c36d673053055fd081e59` is stale. The 2026-11-18 comparison against the current integration head reports 25 commits ahead and 26 behind. PR #29 has ported and hardened the lease changes on top of the integration branch and is the active integrated candidate. Retain PR #28 as the original implementation/reference; do not merge it independently or rewrite its history.

## Decision

PR #29 is the active integrated Draft candidate, based on `integration/humanity-one-0.1`; PR #26 remains the integration-foundation reference and PR #28 remains the original lease implementation/reference. The next gates are clean-machine owner setup and backup/restore/import validation, accessibility and governance decisions, and reconciliation of the full stacked history against `main`. Deployment must stay within the documented same-host/local-SQLite support boundary. No merge or deployment is authorized by this plan.


## CI and branch reconciliation update — 2026-11-17 12:40 UTC+2

- CI `43970440846` completed successfully: all 10 quality steps passed, including Ruff, pytest, pip-audit, wheel/sdist builds, archive verification, and fresh-virtualenv installed-app smoke checks.
- Automatic CI `43970528285` completed successfully on integration head `a55861673e5fea8e3ff8a7a20bcfdfa26700e447`.
- PR #26 and PR #28 remain open Drafts. Both have zero submitted reviews and zero inline review threads at this check.
- Historical topology snapshot (2026-11-17): integration branch was 407 commits ahead and one behind `main`; PR #28 was reported 25 commits ahead and 22 behind. These figures are superseded by the 2026-11-18 snapshot below.
- No merge, force-push, ref rewrite, release, deployment, manual workflow dispatch, or production operation was performed.


## Current integration snapshot — 2026-11-18

- Active integrated candidate: PR #29, `fix/agent-lease-side-effects-audit` at `35cc1abef5e3097e519a728a4205c663db4c6d2f`, based on `integration/humanity-one-0.1`. It is open, Draft, and GitHub reports it mergeable.
- PR #29 is 31 commits ahead and zero behind its integration base. Its latest CI run [44279992873](https://github.com/JoTalbot/humanity-os/actions/runs/44279992873) passed: Ruff, 146 pytest tests, pip-audit, wheel/sdist build, distribution-content verification, and clean-virtualenv installed CLI/app/HTTP smoke checks. The two added CLI regression tests cover backup creation/verification and restore with a verified pre-restore safety backup. One existing Starlette TestClient deprecation warning remains.
- PR #26 remains the integration-foundation Draft on its original source-grounded-context base. PR #28 remains the original Agent Runtime lease implementation Draft. PR #29 contains the integrated and hardened lease implementation; PR #28 is retained for traceability and must not be merged independently.
- The current PR #29 branch compared with `main` is 442 commits ahead and one behind, with divergent history. PR #28 compared with the current integration branch is 25 commits ahead and 26 behind. These are explicit stack-reconciliation blockers; no merge, rebase, cherry-pick, force-push, or ref rewrite was performed.
- Project-owned validation includes authentication and authorization regression tests, dependency auditing, lease fencing, transaction tests, and recovery tests.
- No PR was merged, no release was tagged, no deployment was performed, and no production operation was authorized.


- CI update after the 2026-11-18 documentation and backup/restore test batch: [run 44279992873](https://github.com/JoTalbot/humanity-os/actions/runs/44279992873) passed all quality steps on head `bd63fe951377be1c3b82b8bb4087609f7bb89737`; 146 tests passed, one Starlette TestClient deprecation warning. The branch is 31 commits ahead and zero behind `integration/humanity-one-0.1`, and 442 commits ahead / one behind `main` (diverged). The new tests exercise CLI backup, backup verification, restore, and preservation of the pre-restore state in a safety backup. Clean-machine, cross-platform owner setup and operational recovery remain unvalidated; manual acceptance is deferred by the owner and is not a current gate.


## Current integration snapshot — 2026-11-18

- Active candidate: PR #29, head `2f27e73cbcc9ba2af990a445ff858ce7d275adfc`, based on `integration/humanity-one-0.1`. PR remains open and Draft.
- Live comparison: 48 commits ahead / 0 behind integration; 459 ahead / 1 behind `main`. The merge base with `main` is `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- CI [44282867903](https://github.com/JoTalbot/humanity-os/actions/runs/44282867903) passed all 10 quality steps on this exact head: Ruff, 147 pytest tests, dependency audit, wheel/sdist build, distribution verification and clean-venv packaged-app smoke test. One Starlette TestClient deprecation warning remains.
- History reconciliation finding: `main` has one commit absent from integration, adding an earlier `tests/test_memory.py`. The candidate contains a later expanded version. Its coverage was compared and missing edge assertions were carried forward: append-only event deletion is rejected, and archived memory plus its lifecycle events survive portable export/import. This preserves the relevant test intent without replaying an obsolete file revision.
- The integration branch is the active development line; `main` is behind that line and contains the one separate test commit. Git history itself is still divergent. No rebase, cherry-pick, force-push, ref rewrite or merge was performed.
- Issue #2 implementation is present: authentication defaults to fail-closed, owner setup is an explicit local CLI operation, and ASGI middleware rejects non-loopback peers. Clean-machine operator acceptance remains separate.
- Issue #4 implementation is present: versioned workspace export schema 1.3.0, SHA-256 integrity metadata, secret exclusion, validated import with pre-import backup, and offline confirmed deletion with verified pre-delete backup plus WAL/SHM handling. Issues #2 and #4 remain open pending integrated acceptance.
- PR #26 and #28 remain provenance references; #29 is the single integrated candidate.
- No merge, release or deployment was performed.

## Remaining gates (current)

1. Prepare a provenance-preserving history reconciliation plan for the one main-only test commit and stacked PR history; no history operation is authorized yet.
2. Resolve encryption/key recovery, privacy/legal disclosures, retention and backup-disposal policy decisions.
3. Finalize license, governance, contribution rules and release provenance.
4. Define accessibility and supported desktop/mobile scope.
5. Assemble automated HUMANITY ONE 0.1 RC evidence against the exact candidate HEAD.

Manual operator acceptance and clean-machine backup/restore/import walkthroughs are deferred by owner and are not current gates. Their status remains unvalidated, not passed.


## Current candidate update — 2026-11-18 (latest verified)

- Active candidate: PR #29, branch `fix/agent-lease-side-effects-audit`, Draft, based on `integration/humanity-one-0.1`.
- Latest CI [44283534176](https://github.com/JoTalbot/humanity-os/actions/runs/44283534176) completed successfully on head `4fdf0ff42b4c87f765493dba1ef6d3305a483839`: all 10 steps passed, including Ruff, 147 pytest tests, dependency audit, wheel/sdist build, distribution-content verification and clean-venv packaged HTTP smoke test.
- Added `docs/OPERATOR_ACCEPTANCE.md` with a clean-machine procedure for owner setup, local login, knowledge/document and memory workflows, SQLite backup/restore, portable import into an isolated workspace and an evidence record. The procedure is documented but has not been executed on a clean external machine.
- Corrected `product/ACCEPTANCE_CRITERIA.md` to distinguish implemented capabilities from deferred work and linked the operator runbook.
- Rewrote `docs/RELEASE_READINESS.md` so it reflects the current implementation, latest CI evidence, actual 0.1 limitations and explicit release blockers.
- Main-only memory test intent is represented in the candidate: archived state and lifecycle events survive portable export/import; append-only event deletion is rejected. Git ancestry itself remains divergent.
- No rebase, cherry-pick, force-push, ref rewrite, merge, tag, publication, deployment or production operation was performed.


## Candidate verification update — 2026-11-18

- Code candidate head before this documentation synchronization: `139793dbbaa5ed0000d29108e60a4c428516d6e1` on PR #29.
- GitHub Actions run [44284176087](https://github.com/JoTalbot/humanity-os/actions/runs/44284176087) completed successfully on that code head. PR #29 records 10/10 quality steps passing, including 147 pytest tests, Ruff, dependency audit, wheel/sdist build, distribution verification and clean-virtualenv packaged-app HTTP smoke checks.
- The release-readiness document was synchronized to this latest CI evidence. A documentation-only commit follows the verified code head; any automatic CI triggered by that push is separate evidence and must be checked before claiming the updated PR head is green.
- Manual operator acceptance is deferred by owner. Git-history reconciliation, privacy/key-recovery decisions, governance/license, accessibility and supported-platform scope remain open.
- PR #29 remains Draft. PR #26 and #28 remain provenance references; PR #28 must not be merged independently. No merge, release, deployment, tag, or history rewrite was performed.


## Final candidate status — 2026-11-18 (supersedes earlier snapshots)

- Active candidate is PR #29, branch `fix/agent-lease-side-effects-audit`, base `integration/humanity-one-0.1`, open Draft.
- Current candidate head before this documentation batch was `17a2258842921c74126113141fdcea8ce90be839`.
- GitHub Actions [44284661349](https://github.com/JoTalbot/humanity-os/actions/runs/44284661349) completed successfully on that exact head. All 10 quality steps passed, including lint, tests, dependency audit, wheel/sdist build, distribution verification and clean-virtual-environment packaged-app HTTP smoke test.
- The release-readiness register has been consolidated and synchronized to that CI result. This documentation commit is newer than the verified head; its automatically triggered CI must pass before claiming the new HEAD is green.
- The branch remains divergent from `main` (latest comparison before this documentation batch: 470 ahead / 1 behind). The candidate's integration-base comparison before this documentation batch was 59 ahead / 0 behind. These are topology facts, not merge-readiness approval.
- The main-only memory-test intent is covered in the candidate's expanded test suite; Git ancestry itself is not reconciled. Do not blindly merge, rebase or cherry-pick the stacked branch chain.
- Manual operator acceptance is deferred by owner and remains unvalidated. Legal/privacy/key-recovery, retention, license, governance, accessibility and supported-platform decisions remain open.
- PR #26 remains the integration-foundation reference. PR #28 remains the original lease implementation/reference and must not be merged independently. PR #29 is the sole integrated candidate.
- No merge, rebase, cherry-pick, force-push, ref rewrite, tag, publication, deployment or production operation was performed.

## Completion boundary

The software candidate remains a Draft and is not a completed public release. Public release readiness depends on the current gates in [RELEASE_READINESS.md](RELEASE_READINESS.md), automated validation of the exact RC HEAD, and separate owner authorization for integration/publication. Manual clean-machine operator acceptance is deferred and must not be scheduled or represented as completed.


## Live topology and CI correction — 2026-11-18 (supersedes prior numeric snapshots)

A fresh GitHub check after the previous documentation batch found the following exact state:

- PR #29 HEAD at check: `76cbc8f2095d25310b5f927b4c8f90bd835a55cb`; branch `fix/agent-lease-side-effects-audit`; base `integration/humanity-one-0.1`; open Draft.
- CI run [44285074354](https://github.com/JoTalbot/humanity-os/actions/runs/44285074354) completed successfully on that exact HEAD: 10/10 quality steps passed.
- Live compare with `integration/humanity-one-0.1`: 62 ahead / 0 behind.
- Live compare with `main`: 473 ahead / 1 behind; status `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- Earlier numeric snapshots in this file and `docs/RELEASE_READINESS.md` are historical and must not be treated as current.
- The release-readiness file has been synchronized to this state. Its follow-up documentation commit will require its own CI result before the updated HEAD is called green.
- Historical note: clean-machine operator acceptance was previously listed as outstanding. The later owner decision defers that manual procedure; it is not a current gate. The remaining owner/external policy decisions remain open.
- PR #29 remains the sole integrated candidate. PR #26 and #28 remain provenance references. No merge, history rewrite, tag, publication or deployment was performed.


## Owner workflow decision update — 2026-11-18

- Independent security review is not part of the project plan or a release prerequisite. Do not schedule, request, or block implementation on a separate independent review.
- Continue ordinary engineering review of changed code and preserve documented technical limitations; removing the separate review gate does not remove the need to understand or document those limitations.
- Development cadence follows `docs/DEVELOPMENT_CADENCE.md`: no full CI on every feature push, focused checks only after completed feature batches or changes to critical invariants, and one full validation campaign at the HUMANITY ONE 0.1 release-candidate milestone.
- Do not manually dispatch workflows or run broad test campaigns during routine implementation.
- This owner decision supersedes earlier plan language that listed independent security review as a required gate.


## Live topology correction — 2026-11-18 15:26 UTC+2

Fresh GitHub API comparison after the earlier snapshots:

- PR #29 current head: `d790d3351eab534154709ca0089f210255fdfcac`; base branch `integration/humanity-one-0.1` at `bfaf67c9cfaad81ec66a430c05cc25294f429979`.
- Candidate vs `main`: **576 commits ahead, 1 behind**, status `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- Candidate vs `integration/humanity-one-0.1`: **165 commits ahead, 0 behind**.
- PR #29 remains `open`, Draft; GitHub mergeability metadata is not a substitute for resolving the divergent history.
- This live snapshot supersedes all earlier numeric topology counts in this document. No history rewrite, merge, force-push, test run, workflow dispatch, release or deployment was performed for this correction.


## Owner decision — manual operator acceptance deferred (2026-11-18)

The owner has cancelled the manual operator-acceptance runbook for the current development phase. The clean-machine setup and manual backup/restore/import procedure in `docs/OPERATOR_ACCEPTANCE.md` is retained for reference but is inactive: do not schedule or execute it, and do not require its evidence for current development milestones. Record the capability as deferred/unvalidated, not passed. The current workstream should prioritize implementation, provenance-preserving branch reconciliation, and milestone-based automated checks. Reintroducing manual operator acceptance requires a separate owner decision.


## Live topology and validation snapshot — 2026-11-18

- Measured HEAD: `e6332b81ccdf66b8850cb1397fa219162b5451ed`.
- Candidate vs `integration/humanity-one-0.1`: **177 ahead / 0 behind**.
- Candidate vs `main`: **588 ahead / 1 behind**, `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- PR #29 is open and Draft. Its base is `integration/humanity-one-0.1` at `bfaf67c9cfaad81ec66a430c05cc25294f429979`.
- No combined status checks are attached to this HEAD. No tests or workflows were run during this documentation batch.
- `security/THREAT_MODEL.md` now reflects same-host SQLite lease coordination, clock-skew limitations, the lack of application-level backup encryption, and the owner's deferral of manual operator acceptance.
- The current owner decision remains: manual clean-machine and backup/restore/import acceptance is deferred, unvalidated, and not a current gate.

This measurement is tied to the exact SHA above. The documentation commit that follows changes the branch HEAD; re-run comparisons before any future history operation.
