# HUMANITY ONE Document Intelligence 0.1

## Purpose

Document Intelligence makes private source material searchable while preserving exact provenance. This first slice is local-only and accepts UTF-8 plain text and Markdown.

## Supported contract

- `POST /v1/documents`: JSON body with `filename` and `content`.
- `GET /v1/documents`: bounded metadata listing.
- `GET /v1/documents/{document_id}`: metadata and ordered chunks.
- `POST /v1/documents/search`: bounded lexical search with source references.

The API requires the existing authentication boundary. Requests are limited to 1,000,000 Unicode characters. Accepted suffixes are `.txt`, `.md`, and `.markdown`. Newline endings are normalized to LF. Identical normalized content is rejected rather than silently creating duplicate documents.

Chunks target 1,200 characters with 150-character overlap and prefer newline boundaries. Every chunk stores a stable ID within its document, ordinal, exact half-open character offsets, and SHA-256 content hash. Search returns the document ID, chunk ID, offsets, filename, hashes, and bounded source excerpt. Search is lexical, not semantic, and does not establish relevance or truth.

## Data and privacy

Original text, metadata, and chunks are stored in the local SQLite workspace. Portable workspace export schema 1.2.0 includes document and chunk rows. Schema 1.0.0 imports remain supported and are upgraded with empty document tables. The export integrity digest covers document content; it is not a signature or authenticity proof.

No document content is sent to a model provider. The model gateway remains disabled by default. No embeddings, OCR, external fetch, indexing service, or network integration is used.

## Deliberate exclusions

PDF, DOCX, images, archives, OCR, macros, HTML rendering, and executable attachments are not supported. PDF/DOCX support requires dedicated parsers, decompression/resource limits, malformed-file testing, and security review. A filename extension is not a safe substitute for a parser. Markdown is stored as text and must never be rendered as trusted HTML.

## Operational limitations

This is an early local prototype. There is no document deletion endpoint, retention scheduler, malware scanning, encryption-at-rest guarantee, multi-user authorization, or independent security certification. Operators must protect the database, portable exports, and backups as sensitive personal data.
