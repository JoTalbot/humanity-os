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

- Agent Runtime: event listing is bounded and run completion is single-use; replace unconditional startup recovery with process ownership/lease or heartbeat semantics before multi-worker deployment.
- Citation verification: strictly validate citation identifier syntax and source offsets; document whether citation counts mean unique IDs or occurrences.
- Workspace UI: revalidate authentication, CSRF, loopback restrictions, static asset routing, and behavior with the latest memory schema.
- Deployment: do not describe the current runtime as OS-sandboxed or fully autonomous.

## Safety and release boundaries

- No PR is merged by this plan.
- No production deployment, external integration, outbound message, or real-world action is authorized.
- No CI workflow or test suite has been manually triggered by the integration operator; GitHub's automatic PR CI completed successfully in run `43891172000`.
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


## Reconciliation review — 2026-11-16

- Reviewed the current `main` head against `integration/humanity-one-0.1`.
- The only commit ahead on `main` is `ac46e16728382c0af800421978f0bf7df6943de9` (`test(memory): cover explicit approval and portable lifecycle`), which changes only `tests/test_memory.py`.
- The integration branch already contains a later schema-1.3.0 version of that test module. It covers the same owner-approved memory lifecycle and additionally exercises agent-run/event tables and backward compatibility for workspace schemas 1.0.0–1.2.0. The main-only schema-1.2.0 test file is therefore superseded; do not cherry-pick it over the integrated test suite.
- PR #26 remains based on `humanity-one/source-grounded-context`, not `main`. Its branch has 383 commits ahead and one commit behind `main`; this comparison is not a merge-readiness signal and does not authorize retargeting or merging.
- Reconfirmed the Agent Runtime multi-worker blocker in code: `AgentRuntimeStore.__init__` marks every row with status `running` as interrupted during construction. A second worker starting while another worker owns a live run could incorrectly fail that run. Keep deployment single-process until process ownership plus lease/heartbeat recovery is implemented and tested.
- PR #26 has no submitted reviews or inline review threads. The latest verified automatic CI run is `43931396509` on head `64478ff33d6450f971465aa4e7edccf73d5a5f83`; Ruff, tests and pip-audit passed.
- No branch retarget, merge, force-push, manual test run, workflow dispatch, release or deployment was performed in this review.

## Decision

Keep PR #26 as the integration review candidate. Preserve all source PRs and branches. Do not merge or deploy. The next engineering gate is to design and implement process-safe Agent Runtime leases/heartbeats with deterministic stale-run recovery, then add concurrency-focused tests before considering multi-worker support.
