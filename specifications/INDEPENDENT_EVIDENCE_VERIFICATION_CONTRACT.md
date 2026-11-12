# Independent Evidence Verification Contract 0.1

## Purpose

HUMANITY OS distinguishes a source citation from an assessment of that source. A source being cited, repeated, or linked by several records does not establish independent corroboration. The system records provenance and human review so that later readers can inspect the basis of an assessment.

This contract does not determine whether a claim is true and does not produce an automatic truth score.

## Source identity and lineage

Each embedded `KnowledgeSource` retains its stable, record-local `id` and original `uri`. It additionally supports:

- `source_type`: `primary`, `secondary`, or `unknown`; defaults to `unknown`.
- `independence_group_id`: an optional, explicitly assigned lineage/independence group.
- `derived_from_source_ids[]`: source IDs within the same knowledge record from which this source is known to derive.
- `canonical_uri`: a deterministic comparison value for HTTP(S) URIs. Scheme and host are lowercased, default ports and fragments are removed, and a non-root trailing slash is removed. The original URI is retained.

Canonical URI equality is checked within one knowledge record and duplicate identities are rejected. This is a syntactic normalization only; it does not fetch a URI, follow redirects, prove that two pages contain the same material, or establish publisher identity.

Lineage references must resolve to declared sources in the same record, cannot refer to the source itself, must be unique, and cannot form cycles. The system does not infer lineage or independence from publisher names, URLs, titles, or matching content. Humans or trusted import processes must supply group IDs and derivation links when known.

A syndicated copy or derivative should share the originating `independence_group_id` and identify its parent in `derived_from_source_ids`. Unknown lineage remains unknown; missing metadata must not be interpreted as independence.

## Evidence assessment events

An `EvidenceAssessment` is an append-only event linked to a knowledge record and one of its declared sources. It may optionally identify a specific evidence link on that source.

Fields:

- `knowledge_id`, `source_id`, optional `evidence_id`.
- `stance`: `supports`, `refutes`, or `neutral`.
- `status`: `assessed` or `review_required`.
- `method`: `manual`, `document_review`, `cross_check`, or `automated_triage`.
- required bounded `notes`.
- generated event ID, actor (`owner` or `system`), and assessment timestamp.

A supplied evidence ID must exist on the same knowledge record and refer to the same source. The event is immutable in SQLite; corrections are new assessment events, not edits or deletions. Multiple assessments are allowed and preserve their separate authorship and timestamps.

The current API exposes:

- `POST /v1/evidence-assessments` to append an assessment.
- `GET /v1/evidence-assessments?knowledge_id=...&limit=...` to list assessments for one record.

Both endpoints use the application's existing authentication middleware. Cookie-session actions are attributed to `owner`; bearer-only or unauthenticated local prototype actions are attributed to `system`, consistent with the current Decision Ledger convention.

## Independence semantics

An independence group is an explicit assertion about shared origin or derivation, not a machine-verified fact. Sources in the same group must not be counted as independent corroboration by downstream consumers. A derivative source linked to an origin is not a second independent confirmation merely because it has a different URL or publisher label.

The current release stores the metadata needed for downstream grouping and review. It deliberately does not calculate a credibility score, count independent confirmations, or automatically upgrade a claim's confidence. Conflicting assessments remain visible as separate events and require human interpretation.

## Backup and compatibility

Assessments are stored in a separate SQLite table in the same database. Backup verification validates every assessment payload. The schema is created idempotently and is re-created during store initialization after restoring an older snapshot. Existing knowledge records remain compatible because the new source fields have defaults.

## Explicit non-goals

This contract does not provide network fetching, redirect resolution, content fingerprinting, publisher authentication, cryptographic signatures, external timestamping, automated fact checking, truth certification, source reputation scoring, or a democratic review/quorum protocol. These require separate threat modelling and governance decisions.
