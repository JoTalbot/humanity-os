# Claim-Centric Knowledge Graph Contract 0.1

## Purpose

The knowledge store retains documents, observations, hypotheses, and other knowledge records. The claim graph adds a finer-grained layer: individually addressable propositions grounded in those records. One long document can support multiple claims, and a single claim can be connected to evidence already recorded on its source knowledge record.

A claim node is a structured representation of a proposition, not a declaration that the proposition is true.

## Claim node

A `ClaimNode` contains:

- stable claim ID and the ID of its parent knowledge record;
- a bounded statement, with optional subject, predicate, object, scope, and temporal scope;
- polarity (`affirmed`, `negated`, `unknown`);
- modality (`asserted`, `possible`, `necessary`, `conditional`);
- IDs of evidence links declared on the parent knowledge record;
- actor and creation timestamp.

The parent record must exist and have kind `claim`. Every evidence ID must resolve to an evidence link on that exact record. Evidence is not copied into the claim node, avoiding divergent duplicates. A claim may have no evidence links when it is explicitly a hypothesis or an unverified proposition; absence of evidence is not evidence of falsity.

## Typed relations

A `ClaimRelation` links two distinct existing claim nodes and records a rationale, actor, and timestamp. Supported relations:

- `supports`: the source proposition provides support for the target proposition.
- `contradicts`: the propositions are considered inconsistent in the reviewer's stated scope.
- `depends_on`: the source proposition depends on the target proposition.
- `refines`: the source proposition narrows or makes the target more precise.
- `duplicates`: the reviewer considers the propositions semantically duplicative.

Contradiction and duplicate relations are symmetric and stored in canonical endpoint order. Other relations are directed. Duplicate edges of the same type are rejected. Dependency edges are checked for cycles and a cycle-producing edge is rejected. Other relation types are not interpreted as a logical proof system.

The relation rationale is mandatory. A contradiction is a recorded review assertion, not a machine-proven logical inconsistency. Scope and time must be considered by human reviewers before resolving apparently conflicting claims.

## API

- `POST /v1/claims`: create a claim node.
- `GET /v1/claims?knowledge_id=...&limit=...`: list claim nodes, optionally filtered by parent record.
- `GET /v1/claims/{claim_id}`: retrieve one claim.
- `POST /v1/claim-relations`: create a typed relation.
- `GET /v1/claim-relations?claim_id=...&limit=...`: list relations, optionally touching one claim.

All endpoints use the application's existing authentication middleware. Cookie-session actions are attributed to `owner`; bearer-only or unauthenticated local prototype actions are attributed to `system`.

## Persistence and lifecycle

Claim nodes and relations are append-only SQLite records. Database triggers reject update and delete. Corrections are represented by new claim nodes and explicit relations; this initial contract does not implement claim supersession or a canonical-current-claim pointer. Foreign keys prevent deleting a knowledge record while claim nodes reference it, and prevent deleting claims while relations reference them.

The claim graph is included in SQLite backup verification and restore. Older backups without claim graph tables remain restorable; schema initialization recreates empty graph tables after restore. Backup verification validates each stored claim and relation payload.

## Safety and interpretation boundaries

This layer does not automatically extract claims from prose, resolve entity identity, infer causal relations, calculate truth or confidence scores, perform theorem proving, crawl external sources, or decide contradictions. It does not treat the number of linked sources as independent corroboration. Claims and edges remain reviewable assertions with explicit provenance.

The current implementation is a local single-owner prototype. It is not a multi-user knowledge graph service, a legal record of collective consent, or a production-ready public platform.
