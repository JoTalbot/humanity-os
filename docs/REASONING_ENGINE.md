# HUMANITY ONE Reasoning Engine 0.1

## Purpose

The Reasoning Engine creates bounded, explainable traversals over owner-authored claims and typed relations. It connects claims to their declared evidence, source provenance, human epistemic assessments, and the latest human review of each evidence/source pair.

It is an evidence-navigation and explanation layer, not an autonomous truth judge.

## Reasoning run

`POST /v1/reasoning/runs` accepts a root claim, query, optional exact scope and temporal filters, and bounded traversal limits. A run records:

- Selected claims and typed relations.
- Traversal paths and explicit contradiction candidates.
- Claim-level epistemic assessments.
- Evidence references with source URI, publisher, content hash, declared independence group and derivation lineage.
- The latest evidence assessment for the exact source/evidence pair, plus any latest source-level assessment.
- Explicit limitations, including graph bounds and the fact that graph traversal is not proof of truth.

Each run is persisted as an append-only snapshot. Later assessments do not rewrite historical runs; a new run captures the then-current review state.

## Evidence assessment semantics

Evidence assessments are append-only human-review events. The Reasoning Engine exposes only the latest event for each `(knowledge_id, source_id, evidence_id)` pair, and includes the latest source-level assessment where `evidence_id` is null.

`review_required` remains a review-required state. Automated triage is not promoted to a human verdict. A later assessment supersedes the current view but does not delete the earlier event.

## Epistemic boundaries

- Claim classifications (`fact`, `hypothesis`, `assumption`, `unknown`) are human-authored assessments.
- Evidence stance (`supports`, `refutes`, `neutral`) is an assessment record, not a mathematical truth score.
- Declared source independence and derivation lineage are not independently authenticated.
- The engine does not fetch external sources or prove semantic entailment.
- Missing assessment means no recorded review, not a verdict of falsehood or truth.
- Contradiction edges are explicit reviewer-authored candidates, not automatically inferred contradictions.

## Validation

The focused Reasoning Engine regression suite covers bounded graph traversal, exact scope filtering, contradiction candidates, append-only run persistence, backup/restore, and inclusion of the latest evidence assessment. These checks must be executed at the next targeted validation milestone; unexecuted tests are not validation evidence.


## Integration with Answer Engine

`POST /v1/answers` can accept a `root_claim_id` and bounded traversal controls. The API creates an immutable reasoning run and supplies a compact representation of the selected claims, typed relations, claim assessments, evidence provenance, and latest evidence assessments to the answer provider, but only after explicit per-request provider consent.

The graph is untrusted explanatory context. It helps organize an answer and surface disagreement; it does not replace local document evidence or establish truth. Factual answer statements must still cite retrieved document passages with `[S#]` labels. The response links back to the immutable reasoning run and reports graph limitations and prompt-context truncation.

Reasoning context is size-bounded before provider transmission. Exact source chunks are re-fetched by document/chunk ID after generation, and full chunk integrity is verified even when the prompt excerpt was truncated.

## Source independence inside reasoning snapshots

Every reasoning run now includes a bounded source-lineage report for the selected claims' parent knowledge records. It exposes explicitly declared independence groups, shared upstream derivation clusters, source lineage status, and unknown lineage. This is the same deterministic metadata analysis exposed by the standalone Evidence Independence API, reused by the Reasoning Engine rather than reimplemented.

The report is limited to 500 declared sources across the selected knowledge records. If that bound is exceeded, the reasoning run remains available but records an explicit limitation and leaves independence unassessed. It does not infer independence from different URLs, publishers, or hashes, and it does not score corroboration or truth. Answer Engine receives a compact, bounded summary of this report when reasoning context is enabled.

## Comparative hypothesis evidence profiles

`POST /v1/reasoning/compare` now reports a profile for each root hypothesis in addition to graph/source overlap. Each profile summarizes the bounded claim count and latest recorded claim classifications, linked evidence count, latest evidence stance counts (`supports`, `refutes`, `neutral`), review states (`assessed`, `review_required`, `unassessed`), distinct source count, declared independence groups, recorded dependency edges, and unknown-lineage source count.

The comparison also identifies evidence links shared across all alternatives and evidence links unique to each alternative. Evidence-link identity is scoped by knowledge record and evidence ID, not by URL alone. A review-required automated triage event is not counted as an assessed link. These are descriptive profiles only: the engine does not calculate a hypothesis winner, truth probability, evidence quality score, or automatic verdict. Each alternative remains a separate immutable Reasoning Run.

## Structured contradiction candidates

Each reasoning run also checks the selected bounded claim set for possible contradictions using a deliberately narrow deterministic rule: the claims must have the same non-empty subject, predicate and object after case/whitespace normalization, the same scope, temporal scope and modality, and opposite explicit polarity (`affirmed` versus `negated`). Matching claims are returned as `potential_contradictions` with the exact basis and both claim IDs.

This is candidate discovery, not natural-language entailment or a semantic contradiction judgment. It does not infer negation from prose, treat `unknown` polarity as opposition, or create graph relations automatically. Explicit reviewer-authored `contradicts` edges remain separately represented by `contradiction_candidates`. Answer Engine receives the bounded structured candidates as untrusted context.

## Temporal claim differences

When two selected claims share the same normalized non-empty subject, predicate and object, scope and modality, but carry different non-empty `temporal_scope` labels, the run reports a `temporal_claim_differences` entry instead of treating opposite polarities as a direct contradiction. The record preserves both claim IDs, both original time labels and whether their polarities are the same or opposite.

This is deliberately label-level only. The engine does not parse arbitrary date expressions, infer chronological order, determine interval overlap, or conclude that a change occurred. Claims with the same time label and opposite explicit polarity remain eligible for structured contradiction candidate detection.

## Declared dependency paths

Reasoning runs expose `declared_dependency_paths`, containing only paths whose every traversed edge is an explicit `depends_on` relation. Each path preserves the ordered claim IDs and relation IDs, so an explanation can be traced to the exact graph records. These edges represent declared dependency, not experimentally established causation. Other relation types remain in the general graph paths and are not promoted into dependency chains.