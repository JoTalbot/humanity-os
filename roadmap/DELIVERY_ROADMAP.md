# Delivery Roadmap

## 0 — Foundation
Deliver constitution draft, architecture, data model, agent contract, threat model, governance, product spec and acceptance criteria. Exit: consistency review complete; open decisions recorded.

## 1 — Personal Core
Implement private workspace, identity, authorisation, event history, storage adapters, versioned full-workspace export, verified deletion, backup and restore. Exit: export coverage and secret exclusion verified; deletion requires an explicit offline confirmation and a verified safety backup; restore demonstrated.

## 2 — HUMANITY ONE
Implement provider-neutral model gateway, document ingestion, source-aware search, provenance, explicit memory, responsive UI and local deployment. Initial local text/Markdown ingestion, chunk-level lexical retrieval, and an explicit owner-approved memory API now exist; PDF/DOCX/OCR, semantic retrieval, answer synthesis with citations, the memory review UI and responsive workspace UI have an initial local implementation; bounded local source-cited context preparation is implemented without model calls, and a separate provider answer flow now requires per-request consent and validates citation labels; formal accessibility review, session management, account recovery, and full primary-journey validation remain open. Exit: primary journey works end-to-end; no model provider receives data without explicit configuration and user disclosure.

## 3 — Agent Runtime
Implement bounded lifecycle, capabilities, approvals, tool adapters, quotas, cancellation and audit. Exit: tests prove agents cannot exceed permissions.

## 4 — Independent review
Threat, privacy, accessibility, dependency, security and documentation reviews. Exit: no unresolved critical issue.

## 5 — Public 0.1
Publish source, specs, reproducible build, deployment/operator guides, known limitations and contribution process. Exit: an independent developer can install, operate and extend the system.

## Later releases
0.2 multi-agent collaboration; 0.3 institutional workspaces; 0.4 opt-in federation prototype; 0.5 education/research workflows; 1.0 after independent implementations and security/governance maturity.

## Delivery discipline
Work in coherent milestone batches. Run targeted checks during development and full integration, migration, recovery and security checks before release. Never claim a test passed unless executed and recorded.
