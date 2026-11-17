# HUMANITY ONE 0.1 Integration Plan

Status: integrated HUMANITY ONE 0.1 draft candidate in PR #26; code from PR #13, #15, #17, #19, #21, #23 and #25 is assembled on this branch
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

## Remaining integration and release gates

- Ported the complete owner-journey acceptance test from #19 and updated its workspace export expectation to schema 1.3.0.
- Review all shared docs and API contracts after the combined UI/context/agent changes.
- Review the current diff for any upstream changes not yet represented; preserve original PRs until review is complete.
- Automatic GitHub Actions CI for PR head `5d077980032ec6b9e82605ab7b8e62a76d28059c` completed successfully in run `43891172000`: lint, test, and dependency vulnerability audit all passed. No test suite or workflow was manually launched.
- Prepare a release-candidate PR only after review and test evidence.

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
7. Keep automatic PR CI green as changes land; reserve independent security review and any manually initiated extended test campaign for a separately authorized release gate.
8. Prepare a release-candidate PR with a change inventory, migration/compatibility notes, security limitations, and test evidence.

## Known hardening items to track

- Agent Runtime: event listing is bounded, run completion is single-use, and PR #28 adds worker identity, expiring leases, heartbeat renewal and atomic stale-run recovery. Production remains single-process until independent security review; the lease design is limited to same-host processes sharing a local SQLite database with reliable locking.
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
- Current comparison against `main` at the latest review: integration branch is 407 commits ahead and one behind, with a divergent stacked history. This is not a merge-readiness signal. Preserve the source branches and review the full commit chain before any merge decision.
- The main-only memory test change remains superseded by the integration branch's schema-1.3.0 test coverage, which includes Agent Runtime audit tables and legacy schema 1.0.0–1.2.0 import compatibility.
- PR #28 now implements process ownership, expiring leases, daemon heartbeat renewal, owner fencing, fork-safe worker identity, and atomic stale-run recovery. Its code CI passed in run `43947884587`; the PR remains open and Draft. Its supported deployment boundary is same-host processes sharing a local SQLite database with reliable locking. No multi-host or network-filesystem guarantee is made.
- CI now includes `integration/**`, builds wheel and sdist archives, checks the CLI entry point and static assets, and installs the wheel into an isolated target for an HTTP smoke test. Run `43969330683` passed on commit `be0ae8118c236e83eb9e62626c1e4570bd4671be`; the test confirmed the installed app serves the workspace root and static assets through a loopback peer. The initial smoke harness failed because its default TestClient peer was non-loopback; the harness was corrected without weakening the product's loopback guard.
- Acceptance criteria and documentation now describe portable workspace schema 1.3.0 and imports from 1.0.0–1.2.0. Clean-machine owner setup, backup, restore and cross-platform recovery remain open.
- PR #26 and #28 have no submitted reviews or inline review threads as of this review.
- No PR was merged, no force-push was performed, no workflow was manually dispatched, and no release or deployment was made.
- Latest verification: CI run `43970440846` passed all 10 quality steps, including lint, tests, dependency audit, wheel/sdist inspection and fresh-virtualenv packaged-app smoke checks. Automatic CI run `43970528285` also completed successfully on integration head `a55861673e5fea8e3ff8a7a20bcfdfa26700e447`. No manual workflow dispatch or out-of-CI test run was performed.
- Latest comparison against `main`: integration branch is 407 commits ahead and one behind (`main` head `ac46e16728382c0af800421978f0bf7df6943de9`). The large divergent history remains a manual reconciliation gate, not a merge-readiness signal.
- PR #28's head remains `229cc91266b43452ec79f7e7f72e981344f025e5`; its recorded base SHA `9804c7c3df31608cf47c36d673053055fd081e59` is older than the current integration head. Comparing the PR branches now reports 25 commits ahead and 22 behind. The available GitHub operations do not expose a safe branch-update/cherry-pick workflow, so no history rewrite or ref movement was attempted. Reconcile the stack before merge; both PRs remain Draft.

## Decision

Keep PR #26 and PR #28 as Draft review candidates. The next gates are independent security review of the lease and integrated API/data boundaries, clean-machine owner setup and backup/restore/import validation, accessibility and governance review, and full stacked-history review. Production remains single-process until the lease design and integrated release are independently reviewed. No merge or deployment is authorized by this plan.


## CI and branch reconciliation update — 2026-11-17 12:40 UTC+2

- CI `43970440846` completed successfully: all 10 quality steps passed, including Ruff, pytest, pip-audit, wheel/sdist builds, archive verification, and fresh-virtualenv installed-app smoke checks.
- Automatic CI `43970528285` completed successfully on integration head `a55861673e5fea8e3ff8a7a20bcfdfa26700e447`.
- PR #26 and PR #28 remain open Drafts. Both have zero submitted reviews and zero inline review threads at this check.
- Current topology: integration branch is 407 commits ahead and one behind `main`; PR #28 is 25 commits ahead and 22 behind the current integration branch. Both comparisons are divergent and block merge consideration pending explicit stack reconciliation.
- No merge, force-push, ref rewrite, release, deployment, manual workflow dispatch, or production operation was performed.
