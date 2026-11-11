# Security Threat Model 0.1

## Assets
Personal data, credentials, keys, private knowledge, agent permissions, federation trust, audit history, software supply chain and availability.

## Threats and controls
- Prompt injection: retrieved content is untrusted data; isolate instructions from data.
- Excessive agent authority: capability allowlists, short-lived scoped grants, approval gates.
- Provider leakage: data classification, minimisation, provider disclosure and local-model option.
- Account takeover: strong authentication, recovery controls and session revocation.
- Federation spoofing: signed node identity, key rotation and revocation.
- Malicious update: reproducible builds, signed releases, provenance and review.
- Audit tampering: append-only design, external checkpoints and access separation.
- Data loss/ransomware: encrypted backups and tested restore.
- Hallucinations: evidence references, uncertainty labels and independent verification.
- Denial of service: quotas, rate limits and graceful degradation.

## Invariants
Private by default; no self-escalation; external side effects authorised and audited; secrets excluded from prompts/logs by default; federation opt-in and revocable; security failure stops the affected operation.

## Release gates
Threat model review, dependency/secret scanning, authentication tests, restore demonstration, export/deletion verification, independent security review before broad public deployment.

Prepare incident contacts, severity levels, containment, evidence preservation, notification criteria and post-incident review before production.
