

## Development cadence update (2026-11-18)

Development now uses the milestone-based validation policy in [DEVELOPMENT_CADENCE.md](DEVELOPMENT_CADENCE.md). Full CI no longer runs on every feature-branch push; it runs on pushes to main and by explicit manual dispatch. Targeted checks are reserved for completed feature batches and changed critical invariants. Full regression, packaging, dependency audit and packaged-app smoke validation remain a deliberate HUMANITY ONE 0.1 RC gate.

The successful CI run recorded above belongs to the earlier candidate HEAD stated in that section. The workflow-trigger change and documentation updates made after that run have not been revalidated by a new CI run. Do not describe the current branch HEAD as CI-validated until the full workflow is manually dispatched against that exact commit.


## Follow-up implementation batch — 2026-11-18

- Serialized Agent Runtime first-start schema creation and legacy lease-column migration under SQLite `BEGIN IMMEDIATE`, preventing concurrent same-host workers from racing duplicate `ALTER TABLE` operations.
- Added a focused regression test for two concurrent initializers migrating the same legacy database.
- Updated `docs/AGENT_RUNTIME.md` with the startup/migration guarantee.
- No tests or workflows were run for this small implementation batch, in accordance with the milestone-based validation cadence. The new regression test is pending the next focused Agent Runtime validation batch.
- The candidate HEAD recorded when this note was first added is historical; it is not the current branch HEAD. Previously recorded successful CI runs apply only to their exact historical commit SHAs.


## Source-grounded answer integration — 2026-11-18

- Added authenticated `POST /v1/answers` to connect local bounded document retrieval to the explicitly injected provider-neutral Model Gateway.
- Provider processing requires per-request `allow_provider_processing: true`; the default is false. No provider is configured by default, so consent cannot activate outbound traffic by itself.
- Generated output must cite one or more supplied `[S#]` labels unless it returns the documented insufficient-evidence response. Unknown/missing citation labels are rejected.
- Response includes source document/chunk provenance and explicitly reports that semantic entailment is not verified. Prompts, completions and answers are not persisted by this route.
- Added focused API tests for consent, success/provenance, missing citations, default authentication and absent provider. Tests have not yet been run.


## Evidence integrity follow-up — 2026-11-18

- The source-grounded answer service now re-fetches and verifies every full source chunk after the provider returns, checking current document/chunk hashes and provenance before any answer is returned.
- If a cited source was edited, deleted or otherwise no longer matches the retrieved evidence during generation, the answer is discarded and `POST /v1/answers` returns HTTP 409 for a fresh-context retry.
- Added a focused regression test that mutates a source during the provider call and expects fail-closed behavior.
- Tests and workflows have not been run for this increment. The targeted Agent Runtime and Answer Engine checks remain queued for the next validation milestone; no CI-green claim is made for the current HEAD.
