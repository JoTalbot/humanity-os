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
