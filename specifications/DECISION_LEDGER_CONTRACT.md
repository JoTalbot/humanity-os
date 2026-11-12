# Decision Ledger Contract 0.1

## Purpose

HUMANITY OS records consequential decisions as inspectable evidence of how the system and its human stewards reached a choice. A decision is not merely a mutable configuration value.

## Required decision content

Every decision contains a stable ID and timestamp; title and question; decision context; at least two distinct non-empty alternatives; one selected option matching a declared alternative; a non-empty rationale; optional confidence from 0 to 1; optional references to existing knowledge records; actor attribution (owner or system); and an action (made, reaffirmed, reversed, superseded).

Related knowledge IDs are checked against the current knowledge store at creation. The stored decision preserves its original references and text; it does not silently rewrite if referenced knowledge later changes.

## Immutability and lifecycle

Decision rows are append-only. SQLite triggers reject update and delete operations. A correction must be represented by a new decision entry rather than editing the historical one. The action and supersedes_decision_id fields provide schema vocabulary for future explicit reversal and supersession workflows; 0.1 does not yet expose those workflows or infer them automatically.

## API

- POST /v1/decisions: create a decision.
- GET /v1/decisions: list newest first, bounded to 1–100.
- GET /v1/decisions/{decision_id}: retrieve one immutable decision.

The existing authentication middleware protects these routes whenever owner authentication or a bearer token is configured. Session-authenticated decisions are attributed to owner; unauthenticated local prototype decisions are attributed to system.

## Backup and restore

Decision rows are part of SQLite snapshots. Backup verification validates every decision payload. Legacy databases without the decision table are migrated by schema initialization; historical decisions from before this feature cannot be reconstructed.

## Boundaries and future governance

This is a local single-owner ledger, not a democratic decision protocol or legal record of humanity-wide consent. Multi-steward quorum, signed approvals, public deliberation, appeals, revocation workflows, cryptographic chaining, and external anchoring require separate governance decisions and security review. No AI agent may claim a human decision or attribute its own proposal to the owner.
