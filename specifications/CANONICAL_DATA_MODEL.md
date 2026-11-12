# Canonical Data Model 0.1

All objects have stable opaque IDs, schema versions, timestamps, and explicit visibility.

- **Person:** human profile; no global identity requirement.
- **Identity:** credential/assertion with issuer, key reference, validity and revocation.
- **Knowledge:** versioned claim, concept, procedure, observation, hypothesis, question, dataset or document.
- **Evidence:** source/observation related by supports, contradicts, contextualises, reproduces or derived_from.
- **Agent:** declared purpose, responsible owner, runtime, optional model, policy and capabilities.
- **Task:** goal, constraints, risk, status, approval requirements and lifecycle timestamps.
- **Event:** actor, event type, subject, occurrence/recording time, correlation ID and integrity proof.

## Common rules
- RFC 3339 timestamps with timezone.
- Explicit schema versions.
- Visibility is private, shared, or public; default is private.
- Retention, deletion and export semantics are documented per object.
- Content hashes support integrity, not truth.
- Unknown remains unknown. Conflicting claims coexist and are not resolved by popularity or model confidence alone.
- Internal storage is implementation-specific; canonical JSON schemas and serialisation profiles are public.
