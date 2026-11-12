# HUMANITY ONE 0.1 — Product Specification

## Promise
A person creates a private knowledge workspace, connects a model of choice, works with personal documents, builds useful memory and exports their data at any time.

## Primary journey
Install locally or use a clearly identified hosted instance → create private workspace → configure provider/local model → add documents/notes → ask questions with source references → explicitly save selected memory → inspect, correct, export or delete data.

## Included
Target scope: responsive web UI; private workspace and authentication; provider adapter; document/note ingestion; search; source-aware answers; explicit memory review; task history; API docs; local deployment guide. Current prototype exposes memory lifecycle through authenticated APIs, not a completed responsive UI.

## Current implementation boundary

The current prototype accepts UTF-8 plain text and Markdown up to 1,000,000 characters per document, preserves chunk offsets, and includes document content in portable workspace export schema 1.2.0. Explicit memory proposals require a separate owner approval request; lifecycle events are auditable and model output cannot silently save memory. A retrieval-only context endpoint now returns bounded, source-linked excerpts and a deterministic manifest without calling a model. PDF, DOCX, OCR, semantic retrieval, model-backed answer synthesis with verified citations and responsive review/workspace UI remain future work.

## Excluded
Federation sync, public knowledge marketplace, autonomous external actions, global identity, social network, automated certification, self-modifying agents.

## Principles
No silent memory writes. Distinguish sourced material from model-generated content. Show uncertainty. No external side effects without authorisation. Hosted service is not the only deployment path.

## Non-functional targets
WCAG 2.2 AA target; documented export; private-by-default access; tested backup/restore; privacy-preserving diagnostics; versioned APIs and migrations.

## Success
A new user completes the primary journey; export is inspectable and re-importable; model provider can be changed without losing data; sourced and unsourced answers are distinguishable.
