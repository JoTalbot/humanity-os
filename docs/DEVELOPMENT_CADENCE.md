# Development cadence

## Goal

Optimize for implementation throughput while preserving confidence in critical data and authorization boundaries. The default development loop is implementation-first and milestone-based, not test-after-every-commit.

## Default validation policy

| Change type | During implementation | Milestone / release |
| --- | --- | --- |
| Documentation, comments, formatting | No test run | Review rendered diff |
| Isolated UI or non-critical logic | No automatic full suite | Targeted smoke check when the block is complete |
| Feature implementation across modules | One focused test selection after the feature batch | Regression suite at the next integration milestone |
| Storage, migrations, backup/restore, import/export | Targeted tests for changed invariants | Full regression + recovery acceptance before RC |
| Authentication, authorization, sessions, CSRF, network boundary | Targeted tests for every changed security invariant | Full suite before RC |
| Dependency, packaging, runtime, or workflow changes | Validate the changed build/configuration path | Full CI before RC |

## CI frequency

- Feature branches do not run the full CI workflow on every push.
- Full CI runs on pushes to main and can be started manually with workflow_dispatch.
- Run a manual full CI campaign after a substantial integrated milestone, before RC, and before a release candidate is promoted.
- Do not rerun a successful workflow without a code/configuration change, a relevant external dependency change, or a concrete failure signal.
- When a workflow fails, rerun only the failed job where possible; do not repeat successful jobs without cause.

## Test selection

- Prefer the smallest test module or test case that covers the changed behavior.
- Add regression tests for newly discovered defects and critical invariants; do not duplicate existing coverage for unchanged behavior.
- Keep expensive end-to-end, packaging, recovery, and broad integration checks for milestone boundaries.
- Do not remove meaningful existing tests merely to make CI faster. Reduce execution frequency and avoid redundant coverage instead.
- Never report a check as passed unless it was actually executed.

## Release gate

Before HUMANITY ONE 0.1 RC, run the complete configured CI workflow once against the exact candidate HEAD and record its run URL and commit SHA. Complete the separate operator acceptance steps in OPERATOR_ACCEPTANCE.md. Reduced development-time test frequency does not waive release validation.
