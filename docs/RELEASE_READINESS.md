# Current candidate status — 2026-11-18 (latest batch)

- Active candidate: PR #29, open Draft, branch `fix/agent-lease-side-effects-audit`, base `integration/humanity-one-0.1`.
- Topology measured immediately before this status-note commit at HEAD `66eaf0631d9fdb36d9242799afdccb501298fa2f`; this note is a documentation-only commit following that measurement.
- Candidate vs integration base: **186 ahead / 0 behind**.
- Candidate vs `main`: **597 ahead / 1 behind**, status `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- No workflow runs are attached to this exact HEAD. The gateway metadata regression tests were added but have not been executed.
- This batch rejects blank provider/model identifiers, normalizes surrounding whitespace, tightens the regression assertion to the sanitized `ModelProviderFailure` type, and updates the Model Gateway contract documentation.
- Manual operator acceptance remains deferred and unvalidated. Independent security review is not required.
- No merge, rebase, cherry-pick, force-push, ref rewrite, release, publication, or deployment was performed. `main` and the integration base remain untouched.

---

# Current candidate status — 2026-11-18

- Active candidate: PR #29, open Draft, branch `fix/agent-lease-side-effects-audit`, base `integration/humanity-one-0.1`.
- Measured candidate HEAD before this documentation batch: `e6332b81ccdf66b8850cb1397fa219162b5451ed`.
- Candidate vs integration base: **177 ahead / 0 behind**.
- Candidate vs `main`: **588 ahead / 1 behind**, status `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- No combined status checks are attached to the measured HEAD. The current workflow runs on pushes to `main` or manual dispatch; historical CI results do not validate this candidate HEAD.
- Manual operator acceptance, including clean-machine setup and the backup/restore/import walkthrough, is **DEFERRED by owner**. Do not schedule or execute the runbook. Its scenarios remain unvalidated, not passed, and are not current development gates.
- Independent security review is not required and is not a release gate.
- Do not merge, rebase, cherry-pick, force-push, rewrite refs, publish, release, or deploy without separate authorization. Preserve the one main-only commit and original PR provenance during any future history reconciliation.

The detailed chronological notes below are historical evidence tied to their recorded commit SHAs. They do not override this current status or later owner decisions.

---



## Development cadence update (2026-11-18)

Development now uses the milestone-based validation policy in [DEVELOPMENT_CADENCE.md](DEVELOPMENT_CADENCE.md). Full CI no longer runs on every feature-branch push; it runs on pushes to main and by explicit manual dispatch. Targeted checks are reserved for completed feature batches and changed critical invariants. Full regression, packaging, dependency audit and packaged-app smoke validation remain a deliberate HUMANITY ONE 0.1 RC gate.

The successful CI run recorded above belongs to the earlier candidate HEAD stated in that section. The workflow-trigger change and documentation updates made after that run have not been revalidated by a new CI run. Do not describe the current branch HEAD as CI-validated until the full workflow is manually dispatched against that exact commit.


## Follow-up implementation batch — 2026-11-18

- Serialized Agent Runtime first-start schema creation and legacy lease-column migration under SQLite `BEGIN IMMEDIATE`, preventing concurrent same-host workers from racing duplicate `ALTER TABLE` operations.
- Added a focused regression test for two concurrent initializers migrating the same legacy database.
- Updated `docs/AGENT_RUNTIME.md` with the startup/migration guarantee.
- No tests or workflows were run for this small implementation batch, in accordance with the milestone-based validation cadence. The new regression test is pending the next focused Agent Runtime validation batch.
- The candidate HEAD recorded when this note was first added is historical; it is not the current branch HEAD. Previously recorded successful CI runs apply only to their exact historical commit SHAs.


## Source-grounded answer integration — 2026-11-18

- Added authenticated `POST /v1/answers` to connect local bounded document retrieval to the explicitly injected provider-neutral Model Gateway.
- Provider processing requires per-request `allow_provider_processing: true`; the default is false. No provider is configured by default, so consent cannot activate outbound traffic by itself.
- Generated output must cite one or more supplied `[S#]` labels unless it returns the documented insufficient-evidence response. Unknown/missing citation labels are rejected.
- Response includes source document/chunk provenance and explicitly reports that semantic entailment is not verified. Prompts, completions and answers are not persisted by this route.
- Added focused API tests for consent, success/provenance, missing citations, default authentication and absent provider. Tests have not yet been run.


## Evidence integrity follow-up — 2026-11-18

- The source-grounded answer service now re-fetches and verifies every full source chunk after the provider returns, checking current document/chunk hashes and provenance before any answer is returned.
- If a cited source was edited, deleted or otherwise no longer matches the retrieved evidence during generation, the answer is discarded and `POST /v1/answers` returns HTTP 409 for a fresh-context retry.
- Added a focused regression test that mutates a source during the provider call and expects fail-closed behavior.
- Tests and workflows have not been run for this increment. The targeted Agent Runtime and Answer Engine checks remain queued for the next validation milestone; no CI-green claim is made for the current HEAD.


## Evidence-aware Reasoning Engine increment — 2026-11-18

- Added latest-per-source/evidence assessment retrieval to the append-only evidence assessment store.
- Reasoning runs now include the latest recorded human evidence assessment for each exact evidence link and the latest source-level assessment, without changing or deleting assessment history.
- The API injects the existing evidence assessment store into the Reasoning Engine; no duplicate assessment ledger is created.
- Added a regression test proving that a later human review is the one surfaced in a new reasoning run.
- Added `docs/REASONING_ENGINE.md` defining the contract and epistemic limits.
- Tests/workflows have not been run for this increment. The Reasoning Engine regression suite remains pending targeted validation.

## Reasoning-to-Answer integration — 2026-11-18

- `POST /v1/answers` can now accept an optional root claim and bounded traversal controls, create an immutable reasoning run, and provide a compact representation of claims, typed relations, claim assessments, evidence provenance, and latest evidence assessments to the provider.
- The graph is explicitly marked as untrusted explanatory context. Factual answer claims still require `[S#]` citations to local document passages; semantic entailment remains unverified.
- Explicit provider consent is checked before the reasoning run is created when a root claim is supplied. No provider or external integration was added.
- Reasoning context is size-bounded before transmission; response metadata links to the reasoning run and reports prompt-context truncation.
- Exact post-generation source verification now fetches each chunk by document/chunk ID rather than relying on its position in a bounded search result. Full-chunk verification works when the prompt excerpt is truncated.
- Added integration regression coverage for reasoning context, latest reviewed evidence, and truncated source excerpts.
- Tests/workflows have not been run for this increment. Targeted Answer Engine and Reasoning Engine validation remains outstanding.

## Source-lineage integration — 2026-11-18

- Reasoning Runs now embed the bounded Evidence Independence report for the selected claims' parent knowledge records.
- The report surfaces declared independence groups, shared upstream derivation clusters, and unknown lineage. It does not infer independence from URLs, publishers or hashes.
- The report is capped at 500 declared sources. If the cap is exceeded, the run remains available and explicitly marks lineage analysis as unassessed.
- Answer Engine receives a compact bounded lineage summary alongside claims, relations and evidence assessments when a root claim is supplied.
- Added regression coverage for dependent-source clusters in reasoning snapshots and assertion that lineage context reaches the answer provider. Tests/workflows have not been run.

## Comparative hypothesis evidence profiles — 2026-11-18

- Extended `POST /v1/reasoning/compare` with per-hypothesis profiles for claim classifications, evidence stance counts, review states, source counts, independence groups, dependency edges and unknown lineage.
- Added shared and hypothesis-specific evidence-link sets, identified by `(knowledge_id, evidence_id)` rather than URL alone.
- Distinguishes manually assessed links from `review_required` triage and truly unassessed links.
- Explicitly remains descriptive; no hypothesis ranking, truth probability, quality score or automatic verdict is produced.
- Added a regression test covering shared/unique evidence and assessed/review-required states. Tests/workflows have not been run for this increment.

## Structured contradiction discovery — 2026-11-18

- Reasoning Runs now detect candidate pairs with matching non-empty structured subject/predicate/object, exact scope/temporal-scope/modality and opposite explicit polarity.
- Candidate records include both claim IDs and a machine-readable basis. They are separate from explicit reviewer-authored `contradicts` graph edges.
- Detection is deterministic and narrow; it does not perform semantic entailment, infer negation from prose, or create graph edges.
- Answer Engine receives bounded potential-contradiction context.
- Added regression coverage for normalized structured matches and propagation into the Answer Engine prompt. Tests/workflows have not been run.

## Temporal consistency and dependency paths — 2026-11-18

- Added `temporal_claim_differences` for matching structured propositions with distinct non-empty time labels; preserves both claims and same/opposite polarity.
- Opposite-polarity claims with distinct time labels are not automatically reported as direct contradiction candidates.
- No date parsing, interval overlap, chronological ordering or change-over-time inference is performed.
- Added `declared_dependency_paths`, containing only traversals made entirely of explicit `depends_on` relations, with exact claim and relation IDs.
- Dependency edges are not described as proven causality. Answer Engine receives bounded temporal and dependency context with explicit caveats.
- Added regression tests for temporal variants, dependency chains and prompt propagation. Tests/workflows have not been run.

## Owner workflow decision update — 2026-11-18

- Independent security review is not required and is not a release gate.
- Retain focused engineering review, explicit technical limitations, and the milestone-based validation policy in `DEVELOPMENT_CADENCE.md`.
- Routine feature work does not trigger broad test campaigns. Run focused checks after completed feature batches or changes to critical invariants; reserve one full configured CI run for the exact HUMANITY ONE 0.1 release-candidate commit.
- No manual workflow dispatch or broad test campaign was initiated by this documentation update.

## Live branch topology snapshot — 2026-11-18

Fresh GitHub comparison after the documentation-alignment batch:

- PR #29 head: `f478bdd1a40c17d0ee995e118917b077b79ffb93` on `fix/agent-lease-side-effects-audit`; base: `integration/humanity-one-0.1` at `bfaf67c9cfaad81ec66a430c05cc25294f429979`.
- Candidate vs integration base: **161 commits ahead, 0 behind**.
- Candidate vs `main`: **572 commits ahead, 1 behind**, comparison status `diverged`; merge base: `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- GitHub currently reports PR #29 open, Draft, and mergeable. This metadata does not resolve the divergent history or authorize merging.
- The current head has no combined commit status checks attached. Historical CI runs do not validate this head.
- The one main-only commit and the full stacked history still require an explicit, provenance-preserving integration decision. Do not attempt a blind merge, rebase, cherry-pick, force-push, or ref rewrite.

This snapshot supersedes all earlier numeric ahead/behind counts in this file and the integration plan. Re-run the comparison before any future integration decision; branch counts are time-sensitive.

## Live branch topology snapshot — 2026-11-18 (governance/roadmap alignment)

- Current PR #29 head: `6f4da5feb8d43e9d8e18c8af1a123837f3c26cb4`.
- Candidate vs `integration/humanity-one-0.1`: **164 commits ahead, 0 behind**.
- Candidate vs `main`: **575 commits ahead, 1 behind**, status `diverged`; merge base remains `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- The PR is open and Draft. GitHub's mergeable flag is metadata only and does not resolve the divergent `main` history.
- Governance and roadmap drafts now distinguish ordinary focused engineering review from a separate independent security review; the latter is not part of the 0.1 delivery plan.
- No tests or workflows were run for these documentation-only updates. The current HEAD has no confirmed CI validation.
- The operator acceptance runbook remains unexecuted; legal stewardship, licensing, identity recovery/MFA, encryption/key recovery, retention guarantees, accessibility target and provider-specific controls remain open decisions.

This snapshot supersedes the previous topology snapshot above.


## Live topology correction — 2026-11-18 15:26 UTC+2

Fresh GitHub API comparison after the earlier snapshots:

- PR #29 current head: `d790d3351eab534154709ca0089f210255fdfcac`; base branch `integration/humanity-one-0.1` at `bfaf67c9cfaad81ec66a430c05cc25294f429979`.
- Candidate vs `main`: **576 commits ahead, 1 behind**, status `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- Candidate vs `integration/humanity-one-0.1`: **165 commits ahead, 0 behind**.
- PR #29 remains `open`, Draft; GitHub mergeability metadata is not a substitute for resolving the divergent history.
- This live snapshot supersedes all earlier numeric topology counts in this document. No history rewrite, merge, force-push, test run, workflow dispatch, release or deployment was performed for this correction.


## Final topology measurement before this snapshot commit — 2026-11-18 15:26 UTC+2

- Measured candidate head: `f5e661b2e54a095313f6d7d2adfaa59a1f994257`.
- Against `main`: 578 ahead, 1 behind (diverged); merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- Against `integration/humanity-one-0.1`: 167 ahead, 0 behind.
- This measurement is intentionally tied to the exact input SHA above; this note itself is a subsequent documentation-only commit. Re-run comparisons before any history operation.


## Owner decision — operator acceptance deferred (2026-11-18)

The owner has cancelled the HUMANITY ONE 0.1 manual operator-acceptance runbook for the current development phase. Do not schedule or execute the clean-machine procedure, backup/restore/import walkthrough, or collect operator evidence as part of current work. The runbook remains archived as reference material only. Its non-execution is not a current development blocker and must not be reported as an active release gate. This decision does not claim that those operational scenarios have passed; their status is deferred/unvalidated. Continue with implementation, branch-history reconciliation, and milestone-based automated validation. Revisit operator acceptance only after a separate owner decision.


## Live topology and validation snapshot — 2026-11-18

- Measured HEAD: `e6332b81ccdf66b8850cb1397fa219162b5451ed`.
- Candidate vs `integration/humanity-one-0.1`: **177 ahead / 0 behind**.
- Candidate vs `main`: **588 ahead / 1 behind**, `diverged`; merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- PR #29 is open and Draft. Its base is `integration/humanity-one-0.1` at `bfaf67c9cfaad81ec66a430c05cc25294f429979`.
- No combined status checks are attached to this HEAD. No tests or workflows were run during this documentation batch.
- `security/THREAT_MODEL.md` now reflects same-host SQLite lease coordination, clock-skew limitations, the lack of application-level backup encryption, and the owner's deferral of manual operator acceptance.
- The current owner decision remains: manual clean-machine and backup/restore/import acceptance is deferred, unvalidated, and not a current gate.

This measurement is tied to the exact SHA above. The documentation commit that follows changes the branch HEAD; re-run comparisons before any future history operation.


## Lease-fenced proposal rollback regression — 2026-11-18

- Added a focused regression test proving that a curator memory proposal and its terminal Agent Runtime event roll back together if lease ownership is lost before the terminal commit.
- The test also verifies that no proposal or proposal audit event survives, and that the still-running invocation is subsequently recovered as interrupted exactly once.
- Implementation is unchanged; this closes a test-coverage gap around the existing single-transaction side-effect fence.
- Test execution and CI were not run for this test-only increment. The check remains pending.
- No merge, history rewrite, release, publication, or deployment was performed.


## Expired-worker lease renewal regression — 2026-11-18

- Added a focused regression test proving that a worker cannot renew an already expired lease or resurrect a run after recovery.
- The test verifies exactly one interrupted transition and preserves the two-event append-only history.
- Runtime implementation is unchanged; this adds coverage for the lease-expiry boundary in the existing conditional update.
- Tests and CI were not run. The new regression remains pending execution.


## Agent lease configuration validation — 2026-11-18

- Agent Runtime now rejects boolean, non-finite, zero and negative lease durations during store construction.
- This prevents invalid configuration such as NaN or infinity from reaching lease-expiry arithmetic and producing undefined runtime behavior.
- Added parameterized regression coverage for zero, negative, NaN, positive/negative infinity and boolean values.
- Updated the Agent Runtime contract and threat model.
- Tests and CI were not run for this increment; the new cases remain pending targeted validation.


### Model Gateway timeout configuration validation — 2026-11-18
- Gateway constructor now accepts only numeric, finite timeout values in the documented 0.1–120 second range; booleans, strings, NaN and infinities are rejected with a stable ValueError.
- Added parameterized regression coverage for invalid timeout configuration.
- Updated the gateway contract documentation. Tests and CI remain unrun for this increment.


### Model Gateway request numeric validation — 2026-11-18
- Model generation requests now reject non-finite temperature values (NaN and positive/negative infinity) while retaining the documented inclusive 0.0–1.0 range.
- Added regression coverage for non-finite values and valid boundary values.
- Updated the public request contract. Tests and CI remain unrun for this increment.


### Citation parsing and reasoning-prompt budget hardening — 2026-11-18
- Citation provenance validation now accepts only the exact lowercase `[src-<24 hex>]` marker format. Malformed source markers are surfaced as explicit unverified checks instead of being silently ignored.
- Added regression coverage for malformed markers.
- Reasoning-to-Answer context preparation now has a last-resort compact fallback when unusually large scalar metadata still exceeds the serialized prompt budget. The fallback drops graph payload rather than sending an oversized context.
- Added regression coverage using pathological oversized metadata and asserting the serialized context stays within 24,000 characters.
- Tests and CI were not run for this increment; the new regression cases remain pending targeted validation.


### Model request input coercion — 2026-11-18
- Temperature validation now rejects booleans and string inputs before Pydantic numeric coercion, in addition to rejecting NaN and infinities.
- Added regression cases for both booleans and numeric-looking strings.
- Tests and CI were not run for this increment; regression coverage remains pending targeted validation.


### Latest measured topology — 2026-11-18
- Candidate HEAD: `6415194717ba1d2293829091feecea93a5b49700`.
- 215 commits ahead / 0 behind `integration/humanity-one-0.1`.
- 626 commits ahead / 1 behind `main`; history remains divergent at merge base `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- No workflow run or commit status is attached to this exact HEAD. The candidate is not CI-validated.
- PR #29 remains open Draft. GitHub reports mergeable, but this does not resolve the divergent `main` history.


### Strict per-request provider consent typing — 2026-11-19
- `allow_provider_processing` now requires an actual JSON boolean. String and numeric lookalikes are rejected at request validation instead of being coerced into consent.
- Omitted consent remains false; provider invocation remains gated by explicit true.
- Added API regression coverage for string and numeric consent values.
- Tests and CI were not run for this increment; targeted validation remains pending.


### Strict provider-consent input and current candidate snapshot — 2026-11-19
- `allow_provider_processing` requires a strict JSON boolean; strings and numeric lookalikes are rejected instead of being coerced into consent.
- Added API regression coverage for string and numeric consent values and documented the request contract.
- Measured implementation HEAD: `cf3e9636119d14132fb9f5df1717ad30a5763ea0`.
- At that HEAD: 220 commits ahead / 0 behind `integration/humanity-one-0.1`; 631 ahead / 1 behind `main`, divergent at `de57a48d8d57c023d02ee1c337e29bb557451a9a`.
- No workflow run or combined commit status is attached to the measured HEAD. The new regression has not been executed.
- PR #29 remains open Draft. No merge, history rewrite, release, publication or deployment was performed.


### Consent regression fixture correction — 2026-11-19
- Restored the `_add_source` test helper assertion after inserting strict-consent cases; the test file structure was re-read from GitHub after the correction.
- New consent tests cover string and numeric values rejected by strict request validation.
- No tests were executed; this correction is source-inspected only.
- Corrected implementation/test HEAD: `68fb246e56b8625d330c667808870f6860ad9a17`.
- No workflow run or commit status is attached to this HEAD.


## SQLite rollback-journal cleanup — 2026-11-19

- Workspace deletion now removes the SQLite rollback-journal (`-journal`) sidecar as well as the main database, WAL and SHM files after the verified safety backup and checkpoint.
- Safety-backup destination checks for both deletion and portable import reject the rollback-journal path, matching the existing database/WAL/SHM protections.
- Portable import removes a stale rollback journal before replacing the active database.
- Updated the workspace-portability regression to exercise the rollback-journal destination guard. Tests and CI were not run for this focused change; the regression remains pending execution.


## SQLite backup and restore sidecar protection — 2026-11-19

- Backup destinations and restore safety-backup destinations now reject aliases of the active database and its `-wal`, `-shm`, and `-journal` sidecars.
- Restore accepts only a regular non-symlink source file, verifies and stages it, checkpoints the active database, removes stale SQLite sidecars, then replaces the database.
- Added parameterized regressions for backup and restore path collisions against the database and all three sidecars.
- Updated local operations guidance. Tests and CI were not run; these new regressions remain pending targeted execution.
