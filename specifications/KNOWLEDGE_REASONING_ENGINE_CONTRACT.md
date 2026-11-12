# Knowledge Reasoning Engine Contract 0.1

## Purpose

The Knowledge Reasoning Engine produces bounded, inspectable explanations over the claim graph. It connects a starting claim to related claims, typed relations, and the evidence links already declared on the claims' parent knowledge records.

A reasoning run is an explanation artifact, not a truth judgment, proof, recommendation, or autonomous decision.

## Request and limits

\`ReasoningQuery\` contains:
- a human-readable query (1–4,000 characters);
- an existing root claim ID;
- maximum traversal depth (0–5, default 3);
- maximum returned nodes (1–50, default 30);
- optional exact-match scope and temporal-scope filters.

The implementation reads at most 100 claims and 100 relations from the graph snapshot. It uses breadth-first traversal, a visited set, a depth limit, and a node limit. It never performs unbounded recursive graph traversal.

Directed relations are followed from source to target. \`contradicts\` and \`duplicates\` are treated as symmetric. Other relation types retain their declared direction.

## Explainability output

Each immutable \`ReasoningRun\` records:
- the original query, root claim, limits and filters;
- selected claim nodes and typed relation records;
- ordered claim-ID paths from the root;
- evidence references resolved through the parent knowledge record's declared evidence and source IDs;
- IDs of explicit contradiction relations found within the selected subgraph;
- limitations, actor and timestamp.

Evidence references preserve source URI/canonical URI, title, publisher, optional content hash, evidence relation, excerpt and locator. The engine does not fetch or authenticate remote sources.

## Scope and time

Scope and temporal-scope filters currently use exact string equality. They are not date interval calculations, ontology matching, or automatic entity resolution. A claim that does not match a requested filter is excluded from traversal. The root claim must match the filters or the request is rejected.

An explicit \`contradicts\` edge is returned as a contradiction candidate only when both endpoints are included in the selected subgraph. The engine does not infer contradictions from text, polarity, dates, or scope fields.

## API

- \`POST /v1/reasoning/runs\`: execute and persist a bounded explanation.
- \`GET /v1/reasoning/runs/{run_id}\`: retrieve an immutable explanation.

Cookie-session actions are attributed to \`owner\`; bearer-only or unauthenticated local prototype actions are attributed to \`system\`.

## Persistence and backup

Reasoning runs are append-only SQLite rows. Database triggers reject update and delete. Backup verification validates every stored reasoning-run payload. Restore recreates the reasoning-run schema after replacing the database, including when restoring a legacy snapshot without the table.

## Safety and interpretation boundaries

- Claims remain human-authored assertions; no \`fact\` label or truth score is inferred.
- A graph path explains recorded relationships; it does not establish logical entailment.
- Contradiction candidates are recorded reviewer relations, not machine-discovered or adjudicated conflicts.
- Evidence links are not independently verified by this engine.
- The graph snapshot cap can make results incomplete; the run records this limitation.
- No AI model is invoked, no external content is fetched, and no message or real-world action is triggered.
- This remains a loopback-only, single-owner prototype, not a production or multi-user reasoning service.


## Human epistemic assessments (0.2)

A claim may receive append-only human assessment events with one classification:

- fact: the reviewer considers the proposition established for the stated context;
- hypothesis: a proposition being evaluated;
- assumption: a proposition provisionally accepted for reasoning;
- unknown: the reviewer explicitly records that the matter is unknown.

Each event requires a rationale, actor and timestamp. Reassessment appends a new event; it never overwrites history. Reasoning runs include the latest assessment for each selected claim. No assessment event means no classification was recorded; it must not be silently converted to unknown.

These labels are reviewer statements, not objective truth guarantees, calibrated probabilities, or machine-inferred conclusions.

API:
- POST /v1/claims/{claim_id}/assessments: append an assessment.
- GET /v1/claims/{claim_id}/assessments: retrieve assessment history.

## Alternative explanation comparison (0.2)

POST /v1/reasoning/compare accepts 2–10 unique root claim IDs and runs the same bounded reasoning query for each root. It returns the individual immutable reasoning runs plus the intersection and per-root differences of selected claim IDs and canonical source URIs.

The comparison is descriptive set overlap only. It does not rank alternatives, calculate likelihood, infer causation, or treat shared source identity as independent corroboration. Each component run is persisted independently in the reasoning ledger. All root IDs and filters are validated before any run is created.

Claim assessment records are included in backup verification and their schema is initialized during restore.


## Evidence Independence Engine (0.3)

POST `/v1/evidence-independence/analyze` accepts 1–50 existing knowledge record IDs and a maximum source count of 1–500. The request is rejected if the selected records exceed the source cap.

The report scopes source IDs and independence-group IDs to their parent knowledge record. Identical local IDs in different records are never merged. It groups only explicitly declared independence groups, follows the declared `derived_from_source_ids` graph to identify shared upstream roots, and lists sources whose independence remains unknown.

A derived-source cluster indicates recorded lineage dependency, not proof that every downstream publication copied every detail. A declared independence group is reviewer-provided metadata, not verified publisher independence. Different URLs, publishers, or hashes are not treated as proof of independent origin.

The analysis is deterministic for a fixed knowledge snapshot, bounded to the request limits, read-only, and does not create an append-only event because it is a reproducible derived report. It does not fetch external sources, authenticate publishers, infer missing lineage, rank evidence, calculate truth scores, or adjudicate claims. Unknown independence remains unknown.


## Evidence Independence Engine (0.3)

POST `/v1/evidence-independence/analyze` accepts 1–50 existing knowledge record IDs and a maximum source count of 1–500. The request is rejected if the selected records exceed the source cap.

The report scopes source IDs and independence-group IDs to their parent knowledge record. Identical local IDs in different records are never merged. It groups only explicitly declared independence groups, follows the declared `derived_from_source_ids` graph to identify shared upstream roots, and lists sources whose independence remains unknown.

A derived-source cluster indicates recorded lineage dependency, not proof that every downstream publication copied every detail. A declared independence group is reviewer-provided metadata, not verified publisher independence. Different URLs, publishers, or hashes are not treated as proof of independent origin.

The analysis is deterministic for a fixed knowledge snapshot, bounded to the request limits, read-only, and does not create an append-only event because it is a reproducible derived report. It does not fetch external sources, authenticate publishers, infer missing lineage, rank evidence, calculate truth scores, or adjudicate claims. Unknown independence remains unknown.
