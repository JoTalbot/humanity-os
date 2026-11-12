# Knowledge Provenance Contract 0.1

## Purpose

Knowledge must remain inspectable. A statement is not made true by being stored, repeated by an agent, or assigned a confidence score. HUMANITY OS stores the relationship between a knowledge record and the sources offered in support, refutation, or context.

## Data model

A knowledge record may contain:

- `sources[]`: stable source ID, URI, optional title and publisher, publication/access timestamps, and optional SHA-256 content hash.
- `evidence[]`: stable evidence ID, a reference to one declared source ID, relation (`supports`, `refutes`, `mentions`, `context`), optional bounded excerpt, and optional locator such as page, section, timestamp, or paragraph.
- Legacy `source_uri` remains accepted for backward compatibility.

Source IDs and evidence IDs must be unique within a record. Every evidence link must reference a source declared in the same record. Hashes must be 64 hexadecimal characters. The system does not fetch, verify, or certify a URI merely because it is stored.

## Semantics

- `supports` and `refutes` describe the author's asserted relationship, not an independently verified conclusion.
- `mentions` indicates that a source discusses the subject without necessarily supporting it.
- `context` provides background.
- Excerpts are user-supplied bounded text. They are not a substitute for the source.
- Missing sources mean provenance is unknown, not that a record is false.
- A source hash identifies bytes only when the caller computed it over a clearly defined representation. The current API stores the supplied digest and does not independently calculate it.

## Privacy and sharing

Knowledge visibility defaults to private. Source metadata and excerpts inherit the parent record's visibility. Sharing a record therefore shares its attached provenance and excerpts; clients must display that consequence before publication.

## Evolution

The fields are additive and default to empty arrays so existing 0.1 records remain readable. A future migration may split sources and evidence into independently addressable records with revision history, content-addressed blobs, verification receipts, and conflict-resolution events. Those features are not implied by this contract.
