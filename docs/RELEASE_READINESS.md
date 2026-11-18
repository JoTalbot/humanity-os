

## Development cadence update (2026-11-18)

Development now uses the milestone-based validation policy in [DEVELOPMENT_CADENCE.md](DEVELOPMENT_CADENCE.md). Full CI no longer runs on every feature-branch push; it runs on pushes to main and by explicit manual dispatch. Targeted checks are reserved for completed feature batches and changed critical invariants. Full regression, packaging, dependency audit and packaged-app smoke validation remain a deliberate HUMANITY ONE 0.1 RC gate.

The successful CI run recorded above belongs to the earlier candidate HEAD stated in that section. The workflow-trigger change and documentation updates made after that run have not been revalidated by a new CI run. Do not describe the current branch HEAD as CI-validated until the full workflow is manually dispatched against that exact commit.


## Follow-up implementation batch — 2026-11-18

- Serialized Agent Runtime first-start schema creation and legacy lease-column migration under SQLite `BEGIN IMMEDIATE`, preventing concurrent same-host workers from racing duplicate `ALTER TABLE` operations.
- Added a focused regression test for two concurrent initializers migrating the same legacy database.
- Updated `docs/AGENT_RUNTIME.md` with the startup/migration guarantee.
- No tests or workflows were run for this small implementation batch, in accordance with the milestone-based validation cadence. The new regression test is pending the next focused Agent Runtime validation batch.
- Latest candidate HEAD at this note: `e41fb1546ec7b77575990ad2ff65fc1c71400145`. The previously recorded successful CI runs apply only to their exact historical commit SHAs, not this HEAD.
