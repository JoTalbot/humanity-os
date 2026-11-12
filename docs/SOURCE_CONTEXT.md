# Source-cited Context Preparation

## API

\`POST /v1/documents/context\` accepts:

- \`query\`: 2–200 characters.
- \`passage_limit\`: 1–10, default 5.
- \`max_context_chars\`: 512–16,000, default 8,000.

The response contains a bounded context string and ordered passages. Each passage includes a citation label, source document ID and filename, document hash, chunk ID and hash, and exact half-open character offsets for the excerpt actually included. If a source chunk does not fit, the excerpt is truncated and its end offset is reduced to match the returned text.

The response explicitly reports \`model_called: false\` and \`external_processing: false\`. This endpoint does not invoke the model gateway, send data to a provider, or persist a memory.

## Interpretation

Retrieval is local lexical matching. It is a convenience for finding candidate source passages, not a truth score, semantic relevance guarantee, or factual verification. A future answer-generation stage must retain citation IDs and source ranges, distinguish supported statements from inference, and require explicit data-transfer consent before any document content is sent to a provider. Provider activation remains separately gated and disabled by default.
