# Reference Architecture 0.1

## Goals
Local-first personal experience; replaceable models, databases, runtimes, and hosting; explicit trust boundaries; interoperable versioned contracts; auditability without centralising personal data; graceful partial-connectivity operation.

## Logical planes
1. **Experience:** web/mobile clients, accessibility, consent and permission controls.
2. **Personal:** private workspace, memory, document ingestion, local search, personal agents, export and deletion.
3. **Intelligence:** model gateway, agent runtime, planner, tool registry, policy enforcement, evaluation and human approval.
4. **Knowledge:** versioned knowledge objects, evidence, provenance, search and conflict records.
5. **Federation:** node identity, signed exchange envelopes, replication policy, trust and revocation.
6. **Core:** identity, authorisation, event journal, schema registry, audit, policy and key-management interfaces.

## Trust boundaries
Client ↔ personal service; personal service ↔ model provider; agent runtime ↔ tools; personal node ↔ remote node; private ↔ public knowledge; administrative plane ↔ user-data plane. Each boundary authenticates, authorises, validates and records security-relevant actions.

## Request lifecycle
User request → data classification → bounded plan → scoped tool permission → human approval for consequential actions → execution → validation → provenance record → user inspection.

## Deployment profiles
Single-user local; personal server; institution with tenant isolation; federation node exchanging only explicitly shared objects.

## Replaceability
Dependencies sit behind versioned adapters. Export uses documented formats. No vendor-specific identifier is the only durable identifier.

## Technology candidates, not mandates
Python for iteration; Rust for selected critical components; HTTP/OpenAPI; PostgreSQL initially; replaceable lexical/vector search; OCI containers; responsive web UI.

## Architecture invariants
Local-first personal data; provider-neutral models; auditable security events; opt-in federation; no autonomous permission escalation or constitutional changes.
