# Federation Protocol Draft 0.1

## Goal
Allow independently operated nodes to exchange explicitly shared knowledge and service metadata without central ownership.

## Principles
Opt-in exchange; mutual authentication; per-object consent; minimal disclosure; revocation; key rotation; versioned schemas; no implicit trust.

## Node descriptor
A signed descriptor contains node ID, protocol versions, supported object types, public endpoints, key references, operator contact and policy summary. It must not expose private infrastructure details.

## Exchange envelope
Protocol version; sender/recipient IDs; message ID; idempotency key; issued-at/expiry; object type/schema; visibility/consent reference; payload/content reference; signature.

A signature proves control of a key, not truth or operator trustworthiness.

## Replication and conflicts
Replication is per collection/object and supports pause, revoke, resynchronise and deletion propagation where possible. Concurrent versions are retained; important conflicts are not silently resolved by last-write-wins.

## 0.1 scope
Design only. Peer discovery and remote synchronisation are deferred until personal data controls and schemas are stable.
