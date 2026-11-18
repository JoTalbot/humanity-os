# Contributing to HUMANITY OS

We welcome contributions that improve human agency, privacy, interoperability, accessibility, safety and long-term maintainability.

## Before coding
- Read the constitution draft and relevant specifications.
- For substantial changes, open an RFC describing the problem, alternatives, risks, migration and compatibility.
- Do not introduce mandatory dependencies on a single AI model, cloud provider or proprietary service.

## Pull requests
- Keep changes focused and documented.
- Add regression coverage for changed behavior and newly discovered defects; avoid duplicating existing coverage.
- Document security and privacy implications.
- Do not include secrets, private user data or unlicensed material.
- Do not claim tests, audits or benchmarks that were not run.

## Validation cadence
Development is implementation-first and milestone-based. Do not run the full test suite after every commit. Prefer targeted checks for changed critical invariants, and reserve full CI, broad regression, packaging and recovery validation for substantial integration milestones and release candidates. Feature branches do not trigger full CI on every push; full CI runs on main and by manual dispatch. See [Development Cadence](docs/DEVELOPMENT_CADENCE.md).

## Decision status
Specifications marked Draft or Open are not settled standards. Raise conflicts through an RFC rather than silently changing their meaning.
