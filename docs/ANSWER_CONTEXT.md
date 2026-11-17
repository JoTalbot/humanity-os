# Source-Grounded Answer Context 0.1

## Contract

`POST /v1/answers/context` prepares a bounded local evidence package for a future answer workflow. It returns `status=context_only` and never generates an answer or calls the Model Gateway.

The request accepts a query, a maximum chunk count, a total source-text character budget, and a per-document chunk limit. The service retrieves only locally stored document chunks. Each included source contains:

- A deterministic citation ID.
- Document and chunk IDs.
- Original filename and media type.
- Document and chunk SHA-256 hashes.
- Exact start/end character offsets.
- The complete, unmodified chunk excerpt.

Chunks are never silently truncated. Sources that do not fit are listed in `omitted` with a reason: `context_budget`, `per_document_limit` or `max_chunks`.

## Trust boundary

Retrieved excerpts are untrusted data. They may contain prompt-injection text, malicious instructions, misleading claims or quoted hostile content. The response carries an explicit instruction boundary stating that excerpts are evidence, not instructions. A future model integration must keep system instructions separate from source text and must not grant source excerpts tool or policy authority.

## Integrity

The response includes `manifest_sha256`, a deterministic SHA-256 digest over the ordered source manifest. This detects accidental changes when recomputed by a client; it is not a digital signature, authenticity proof or encryption. Source IDs, offsets and hashes allow a client to compare each excerpt with the local workspace.

## Safety exclusions

- No model generation or outbound network request.
- No prompt or answer persistence.
- No memory proposal creation or approval.
- No document mutation.
- No claim that retrieved material is true or independent.
- No generated answer is returned by this endpoint.

The current lexical retriever scans local chunks and requires every extracted query term to occur in a chunk. Semantic retrieval, reranking, answer synthesis, citation verification, PDF/DOCX/OCR and a user interface remain future work.

## Citation provenance validation

`POST /v1/answers/validate` accepts answer text, the exact source manifest and its digest. It extracts `[src-<24 hex>]` markers, checks the manifest digest, rejects duplicate manifest IDs, and compares every cited excerpt with the current local document and chunk records, including content hashes, chunk ordinal, offsets, filename and media type.

A `verified` result means only that each cited excerpt is present in the supplied manifest and matches the current local source record. It does **not** prove that the excerpt logically supports the answer, that the source is accurate, or that the answer is true. Semantic support assessment remains a separate future capability.
