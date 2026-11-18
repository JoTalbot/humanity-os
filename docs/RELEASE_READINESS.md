

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