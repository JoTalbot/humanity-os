# Source-Grounded Answer Generation

## Contract

\`POST /v1/documents/answer\` combines local lexical retrieval with the injected provider-neutral Model Gateway. It requires the explicit request field \`allow_provider_processing: true\`. Without that flag, the service rejects the request before retrieving or invoking a provider. With consent but no configured provider, it returns an unavailable response and performs no outbound operation.

\`GET /v1/models/capabilities\` reports whether a provider is configured and exposes its declared provider/model identifiers. It does not probe or activate a provider.

## Processing

1. Retrieve a bounded local context packet using the same source-aware retrieval contract.
2. Construct a transient prompt that treats retrieved text as untrusted data and instructs the provider to cite exact supplied labels such as \`[S1]\`.
3. Invoke only the provider explicitly injected into the application.
4. Validate that every cited label resolves to a source passage. Unknown labels and ordinary uncited answers are rejected. The exact insufficient-evidence response is allowed without citations.
5. Return answer text and only the cited source records, including document/chunk IDs, SHA-256 hashes and exact excerpt offsets.

Prompt and completion content are not persisted by this service. Provider errors remain sanitized. A consented provider may be local or remote; the capability response discloses its declared provider/model IDs, but this prototype does not independently attest provider locality or behavior.

## Important limits

Citation-label validation proves only that labels map to passages supplied in the request. It does not prove that a cited passage semantically entails a claim, that the source is true, or that the answer is unbiased. Review the cited source ranges. The response explicitly reports \`semantic_entailment_verified: false\`.

No real network provider is included or enabled by default. Provider injection is an application configuration boundary, not a user-facing integration wizard. No model calls occur during document ingestion, search or context preparation. Memory writes remain separate and owner-approved.
