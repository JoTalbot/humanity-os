from __future__ import annotations

import hashlib
import json
import sqlite3

from fastapi.testclient import TestClient

from humanity_os.answer_context import AnswerContextBuilder, AnswerContextRequest
from humanity_os.app import create_app
from humanity_os.citation_verification import CitationValidationRequest, CitationValidator
from humanity_os.documents import DocumentStore


def _manifest_digest(sources):
    canonical = json.dumps(
        [source.model_dump(mode="json") for source in sources],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _context(database):
    documents = DocumentStore(database)
    document = documents.create(
        "ukrainian.txt", "КИЇВ зберігає перевірене джерело для HUMANITY OS."
    )
    context = AnswerContextBuilder(documents).build(
        AnswerContextRequest(query="київ джерело")
    )
    return documents, document, context


def test_valid_citation_is_verified_against_exact_local_source(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    documents, document, context = _context(database)
    source = context.sources[0]
    request = CitationValidationRequest(
        answer=f"The statement is sourced [{source.citation_id}].",
        manifest_sha256=context.manifest_sha256,
        sources=context.sources,
    )

    result = CitationValidator(documents).validate(request)
    assert result.status == "verified"
    assert result.verification_scope == "provenance_only"
    assert result.semantic_support_verified is False
    assert result.checks[0].status == "verified"
    stored = documents.get(document["id"])
    chunk = stored["chunks"][source.ordinal]
    assert chunk["content"][source.start_offset - chunk["start_offset"]:] == source.excerpt


def test_unknown_citation_and_missing_citations_are_unverified(tmp_path):
    documents, _, context = _context(tmp_path / "workspace.sqlite3")
    unknown = "src-" + ("0" * 24)
    result = CitationValidator(documents).validate(
        CitationValidationRequest(
            answer=f"Unsupported claim [{unknown}].",
            manifest_sha256=context.manifest_sha256,
            sources=context.sources,
        )
    )
    assert result.status == "unverified"
    assert result.checks[0].reason == "not_in_manifest"

    empty = CitationValidator(documents).validate(
        CitationValidationRequest(
            answer="An answer with no citations.",
            manifest_sha256=context.manifest_sha256,
            sources=context.sources,
        )
    )
    assert empty.status == "unverified"
    assert "no_citations" in empty.reasons


def test_manifest_tampering_and_duplicate_ids_are_rejected(tmp_path):
    documents, _, context = _context(tmp_path / "workspace.sqlite3")
    source = context.sources[0]
    changed = source.model_copy(update={"excerpt": "altered source"})
    tampered = CitationValidator(documents).validate(
        CitationValidationRequest(
            answer=f"Claim [{source.citation_id}].",
            manifest_sha256=context.manifest_sha256,
            sources=[changed],
        )
    )
    assert tampered.status == "unverified"
    assert "manifest_digest_mismatch" in tampered.reasons

    duplicated_sources = [source, source]
    duplicate = CitationValidator(documents).validate(
        CitationValidationRequest(
            answer=f"Claim [{source.citation_id}].",
            manifest_sha256=_manifest_digest(duplicated_sources),
            sources=duplicated_sources,
        )
    )
    assert duplicate.status == "unverified"
    assert "duplicate_manifest_id" in duplicate.reasons


def test_stale_source_is_rejected_even_when_manifest_digest_is_valid(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    documents, _, context = _context(database)
    source = context.sources[0]
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE document_chunks SET content = ? WHERE id = ?",
            ("modified locally", source.chunk_id),
        )

    result = CitationValidator(documents).validate(
        CitationValidationRequest(
            answer=f"Claim [{source.citation_id}].",
            manifest_sha256=context.manifest_sha256,
            sources=context.sources,
        )
    )
    assert result.status == "unverified"
    assert result.checks[0].reason == "source_mismatch"


def test_citation_validation_api_is_authenticated_and_provenance_only(tmp_path):
    strict = TestClient(
        create_app(str(tmp_path / "strict.sqlite3")),
        client=("127.0.0.1", 50000),
    )
    assert strict.post("/v1/answers/validate", json={"answer": "x"}).status_code == 401

    database = tmp_path / "local.sqlite3"
    client = TestClient(
        create_app(str(database), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    client.post(
        "/v1/documents",
        json={"filename": "source.txt", "content": "Local source is traceable."},
    )
    context = client.post(
        "/v1/answers/context", json={"query": "source traceable"}
    ).json()
    source = context["sources"][0]
    response = client.post(
        "/v1/answers/validate",
        json={
            "answer": f"Claim [{source['citation_id']}].",
            "manifest_sha256": context["manifest_sha256"],
            "sources": context["sources"],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "verified"
    assert response.json()["semantic_support_verified"] is False