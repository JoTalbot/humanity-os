# HUMANITY OS

**Open, human-centred intelligence infrastructure for the long-term benefit of humanity.**

## Mission
Expand humanity's ability to understand, learn, create, preserve knowledge, and solve shared problems while protecting human agency.

## Strategic charter
- Mission: human development, civilization development, and scientific progress.
- Stewardship: humanity as the intended beneficiary; no single company, model, or person should control the system.
- Intelligence: hybrid personal + collective.
- Access: open and free core.
- Horizon: continuous evolution without a planned end date.

## Product sequence
1. **HUMANITY ONE** — personal knowledge and intelligence workspace.
2. **HUMANITY NETWORK** — interoperable agents and federated knowledge exchange.
3. **HUMANITY CIVILIZATION** — open infrastructure for education, research, and shared problem-solving.

## First milestone
Build a useful, independently deployable personal product first. The initial release focuses on private knowledge, source-aware assistance, explicit personal memory, portability, and model-provider replaceability.

## Principles
Human agency; personal data sovereignty; open protocols; verifiable knowledge provenance; least privilege; accountable automation; independent implementations; backward-compatible evolution.

## Repository status
The repository contains draft architecture documents and an initial HUMANITY ONE local knowledge API vertical slice. The API persists private-by-default knowledge records in SQLite and provides create/list/read/delete endpoints. It is a local prototype, not production-ready: there is no authentication or multi-tenant isolation. No test execution, security audit, legal review, or ratified public governance is claimed.

See `constitution/`, `architecture/`, `specifications/`, `security/`, `federation/`, `governance/`, `product/`, `roadmap/`, and `docs/`. Run locally with `python -m pip install -e '.[dev]'` then `humanity-os`. The CLI binds only to loopback.
