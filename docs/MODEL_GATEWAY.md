# HUMANITY ONE Model Gateway 0.1

## Status

This document defines the first provider-neutral boundary. The current implementation contains no network-backed provider. The default application has no provider configured and returns HTTP 503 for generation requests until a provider is explicitly injected by the application host.

## Contract

Endpoint: `POST /v1/models/generate`

Request schema version: `1.0`

- `prompt`: required, 1–20,000 characters.
- `system_instruction`: optional, maximum 4,000 characters.
- `max_output_tokens`: 1–4,096, default 512.
- `temperature`: 0.0–1.0, default 0.2.
- Unknown request fields are rejected.

Response includes schema version, provider ID, model ID, output, optional token usage, finish reason and generation timestamp. Provider credentials, endpoint URLs and internal exception details are never returned.

The gateway uses an asynchronous provider protocol and a bounded request timeout (30 seconds by default, configurable in the gateway constructor between 0.1 and 120 seconds). Provider errors are mapped to sanitized HTTP responses: unavailable provider 503, timeout 504, provider failure 502. Input validation errors remain 422.

## Default safety behavior

- No provider is configured by default.
- No environment variable automatically activates a provider.
- No outbound model traffic is made by this release.
- The only provider in this milestone is an in-process deterministic test provider used in tests.
- Prompts and completions are transient request data. The gateway does not persist them, add them to the knowledge store, or write them to the security audit ledger.
- The gateway does not log prompt or completion content.
- The API remains behind the existing authentication and loopback middleware.
- No tools, autonomous actions, external side effects, retrieval augmentation or automatic memory writes are part of this endpoint.

## Future provider activation requirements

A future local or remote adapter must not be enabled merely by installing a package or setting an undocumented environment variable. Before activation, the operator must explicitly configure and review:

1. Provider identity, model identity, endpoint and hosting location.
2. Data classification and exactly which prompt fields can leave the local node.
3. Clear user-facing disclosure and explicit opt-in for remote transmission.
4. Secret injection from a protected runtime secret source; never persist credentials in workspace tables, exports, responses or logs.
5. TLS and endpoint authentication for remote providers.
6. Connection and response timeouts, maximum request/response size, token quotas, rate limits and cost controls.
7. Sanitized error handling, retry policy and failure behavior that does not silently switch providers.
8. Provider retention/training terms and jurisdictional/privacy review.
9. Tests proving no network traffic occurs when disabled and no secret or prompt content leaks to logs.

A future provider switch must be explicit and visible. No provider may be silently selected as a fallback.

## Known limitations

- There is no production model provider adapter.
- There is no streaming response API.
- There is no model selection UI or per-workspace provider configuration.
- A retrieval-only `/v1/answers/context` endpoint now prepares bounded source manifests, but it does not invoke the model gateway, synthesize answers, or verify citations in generated output.
- Token usage is provider-reported and cannot be independently verified by the gateway.
- The timeout bounds the awaited provider call; adapter implementations must also enforce transport-level connection and read timeouts.
