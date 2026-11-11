# Security Threat Model 0.1

## Assets

Personal data, credentials, keys, private knowledge, agent permissions, federation trust, audit history, software supply chain and availability.

## Threats and controls

- Prompt injection: retrieved content is untrusted data; isolate instructions from data.
- Excessive agent authority: capability allowlists, short-lived scoped grants, approval gates.
- Provider leakage: data classification, minimisation, provider disclosure and local-model option.
- Account takeover: strong authentication, recovery controls and session revocation.
- Shared-token disclosure: optional bearer token, cryptographic token generation, constant-time comparison, secret-manager/environment injection, no token persistence in the application database.
- Federation spoofing: signed node identity, key rotation and revocation.
- Malicious update: reproducible builds, signed releases, provenance and review.
- Audit tampering: append-only design, external checkpoints and access separation.
- Data loss/ransomware: encrypted backups and tested restore.
- Hallucinations: evidence references, uncertainty labels and independent verification.
- Denial of service: quotas, rate limits and graceful degradation.

## Invariants

Private by default; no self-escalation; external side effects authorised and audited; secrets excluded from prompts/logs by default; federation opt-in and revocable; security failure stops the affected operation.

## Release gates

The optional bearer token is a local-development control, not a complete identity system. Without it, the service is unauthenticated and must remain loopback-only. Even with it, network exposure remains prohibited until individual identity, scoped authorisation, rate limits, origin policy, TLS/edge configuration, audit events, recovery/rotation procedures, dependency/secret scanning, and independent review are complete.

Threat model review, authentication tests, restore demonstration, export/deletion verification, independent security review before broad public deployment.

Prepare incident contacts, severity levels, containment, evidence preservation, notification criteria and post-incident review before production.
