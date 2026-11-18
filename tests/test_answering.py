from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.model_gateway import ModelUsage, ProviderGeneration


class CitedProvider:
    provider_id = "local-test"
    model_id = "cited-v1"

    async def generate(self, request):
        return ProviderGeneration(
            output="The source confirms the local-first design [S1].",
            usage=ModelUsage(input_tokens=10, output_tokens=9),
            finish_reason="stop",
        )


class UncitedProvider:
    provider_id = "local-test"
    model_id = "uncited-v1"

    async def generate(self, request):
        return ProviderGeneration(output="An unsupported answer without citations.")


def _client(tmp_path, provider=None, authenticated=False):
    app = create_app(
        str(tmp_path / "workspace.sqlite3"),
        allow_unauthenticated_local=not authenticated,
        model_provider=provider,
    )
    return TestClient(app, client=("127.0.0.1", 50000))


def _add_source(client):
    response = client.post(
        "/v1/documents",
        json={
            "filename": "humanity.txt",
            "content": "HUMANITY OS follows a local-first design with owner-controlled data.",
        },
    )
    assert response.status_code == 201


def test_answer_route_requires_explicit_provider_processing_consent(tmp_path):
    client = _client(tmp_path, CitedProvider())
    _add_source(client)

    response = client.post("/v1/answers", json={"query": "local-first design"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Explicit consent for configured provider processing is required"


def test_answer_route_returns_source_linked_answer_after_explicit_consent(tmp_path):
    client = _client(tmp_path, CitedProvider())
    _add_source(client)

    response = client.post(
        "/v1/answers",
        json={"query": "local-first design", "allow_provider_processing": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"].endswith("[S1].")
    assert body["provider"] == "local-test"
    assert body["citations"][0]["filename"] == "humanity.txt"
    assert body["processing"]["provider_processing_authorized"] is True
    assert body["processing"]["semantic_entailment_verified"] is False
    assert body["processing"]["prompt_persisted"] is False
    assert body["processing"]["completion_persisted"] is False


def test_answer_route_rejects_provider_output_without_citations(tmp_path):
    client = _client(tmp_path, UncitedProvider())
    _add_source(client)

    response = client.post(
        "/v1/answers",
        json={"query": "local-first design", "allow_provider_processing": True},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Model response failed citation validation"


def test_answer_route_is_authenticated_by_default(tmp_path):
    client = _client(tmp_path, CitedProvider(), authenticated=True)

    response = client.post(
        "/v1/answers",
        json={"query": "local-first design", "allow_provider_processing": True},
    )

    assert response.status_code == 401


def test_answer_route_requires_a_configured_provider_even_after_consent(tmp_path):
    client = _client(tmp_path)
    _add_source(client)

    response = client.post(
        "/v1/answers",
        json={"query": "local-first design", "allow_provider_processing": True},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "No model provider is configured"


class MutatingProvider:
    provider_id = "local-test"
    model_id = "mutating-v1"

    def __init__(self, database):
        self.database = database

    async def generate(self, request):
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE document_chunks SET content = ? WHERE ordinal = 0",
                ("tampered while generation was running",),
            )
        return ProviderGeneration(
            output="The source confirms the local-first design [S1]."
        )


def test_answer_route_rejects_source_changed_during_generation(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    client = TestClient(
        create_app(
            str(database),
            allow_unauthenticated_local=True,
            model_provider=MutatingProvider(database),
        ),
        client=("127.0.0.1", 50000),
    )
    _add_source(client)

    response = client.post(
        "/v1/answers",
        json={"query": "local-first design", "allow_provider_processing": True},
    )

    assert response.status_code == 409
    assert response.json()["detail"].startswith("A source changed during answer generation")


class ReasoningAwareProvider:
    provider_id = "local-test"
    model_id = "reasoning-aware-v1"

    def __init__(self):
        self.prompt = ""

    async def generate(self, request):
        self.prompt = request.prompt
        return ProviderGeneration(
            output="The source describes the local-first design [S1]."
        )


def test_answer_route_uses_claim_graph_and_latest_evidence_assessment(tmp_path):
    provider = ReasoningAwareProvider()
    client = _client(tmp_path, provider)
    _add_source(client)
    knowledge = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Local-first architecture",
        "content": "The project stores data locally and keeps owner control.",
        "sources": [{
            "id": "source-1",
            "uri": "https://example.org/local-first",
            "title": "Architecture note",
            "publisher": "Project documentation",
        }],
        "evidence": [{
            "id": "evidence-1",
            "source_id": "source-1",
            "relation": "supports",
            "excerpt": "Data remains local.",
            "locator": "section 1",
        }],
    })
    assert knowledge.status_code == 201
    claim = client.post("/v1/claims", json={
        "knowledge_id": knowledge.json()["id"],
        "statement": "The system follows a local-first architecture.",
        "evidence_ids": ["evidence-1"],
    })
    assert claim.status_code == 201
    assessment = client.post("/v1/evidence-assessments", json={
        "knowledge_id": knowledge.json()["id"],
        "source_id": "source-1",
        "evidence_id": "evidence-1",
        "stance": "refutes",
        "status": "assessed",
        "method": "manual",
        "notes": "Reviewer found this excerpt does not establish the full claim.",
    })
    assert assessment.status_code == 201

    response = client.post("/v1/answers", json={
        "query": "local-first design",
        "allow_provider_processing": True,
        "root_claim_id": claim.json()["id"],
    })

    assert response.status_code == 200
    body = response.json()
    assert body["reasoning"]["claim_ids"] == [claim.json()["id"]]
    assert body["reasoning"]["evidence_count"] == 1
    assert "The system follows a local-first architecture." in provider.prompt
    assert "Reviewer found this excerpt does not establish the full claim." in provider.prompt
    assert "refutes" in provider.prompt
    assert "evidence_independence" in provider.prompt
    assert "potential_contradictions" in provider.prompt
    assert body["processing"]["semantic_entailment_verified"] is False


def test_answer_route_verifies_full_chunk_when_prompt_excerpt_is_truncated(tmp_path):
    client = _client(tmp_path, CitedProvider())
    content = "local-first design " + ("additional source material " * 80)
    created = client.post("/v1/documents", json={
        "filename": "long-source.txt",
        "content": content,
    })
    assert created.status_code == 201

    response = client.post("/v1/answers", json={
        "query": "local-first design",
        "allow_provider_processing": True,
        "max_context_chars": 512,
    })

    assert response.status_code == 200
    assert response.json()["citations"][0]["filename"] == "long-source.txt"
