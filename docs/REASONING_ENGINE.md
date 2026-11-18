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
