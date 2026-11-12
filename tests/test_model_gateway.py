import asyncio

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.model_gateway import (
    ModelGateway,
    ModelGenerationRequest,
    ModelProviderTimeout,
    ModelUsage,
    ProviderGeneration,
)


class DeterministicProvider:
    provider_id = "test-provider"
    model_id = "deterministic-v1"

    async def generate(self, request):
        return ProviderGeneration(
            output=f"TEST OUTPUT: {request.prompt}",
            usage=ModelUsage(input_tokens=3, output_tokens=4),
            finish_reason="stop",
        )


class FailingProvider:
    provider_id = "test-provider"
    model_id = "failure-v1"

    async def generate(self, request):
        raise RuntimeError("private prompt must not leak")


class SlowProvider:
    provider_id = "test-provider"
    model_id = "slow-v1"

    async def generate(self, request):
        await asyncio.sleep(0.5)
        return ProviderGeneration(output="late")


def test_default_app_has_no_provider_and_returns_unavailable(tmp_path):
    app = create_app(
        str(tmp_path / "workspace.sqlite3"), allow_unauthenticated_local=True
    )
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/v1/models/generate", json={"prompt": "private content"}
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "No model provider is configured"


def test_injected_provider_returns_versioned_provider_neutral_response(tmp_path):
    app = create_app(
        str(tmp_path / "workspace.sqlite3"),
        allow_unauthenticated_local=True,
        model_provider=DeterministicProvider(),
    )
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/v1/models/generate",
        json={"prompt": "hello", "max_output_tokens": 64, "temperature": 0},
    )

    assert response.status_code == 200
    assert response.json()["schema_version"] == "1.0"
    assert response.json()["provider"] == "test-provider"
    assert response.json()["model"] == "deterministic-v1"
    assert response.json()["output"] == "TEST OUTPUT: hello"
    assert response.json()["usage"] == {"input_tokens": 3, "output_tokens": 4}


def test_generation_request_rejects_oversized_prompt_and_unbounded_settings(tmp_path):
    app = create_app(
        str(tmp_path / "workspace.sqlite3"),
        allow_unauthenticated_local=True,
        model_provider=DeterministicProvider(),
    )
    client = TestClient(app, client=("127.0.0.1", 50000))

    oversized = client.post(
        "/v1/models/generate", json={"prompt": "x" * 20_001}
    )
    unbounded = client.post(
        "/v1/models/generate",
        json={"prompt": "hello", "max_output_tokens": 100_000},
    )

    assert oversized.status_code == 422
    assert unbounded.status_code == 422


def test_provider_failure_is_sanitized_and_prompt_is_not_logged(tmp_path, caplog):
    app = create_app(
        str(tmp_path / "workspace.sqlite3"),
        allow_unauthenticated_local=True,
        model_provider=FailingProvider(),
    )
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/v1/models/generate", json={"prompt": "private prompt marker"}
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Model provider request failed"
    assert "private prompt marker" not in caplog.text
    assert "private prompt must not leak" not in caplog.text


def test_gateway_timeout_is_bounded():
    gateway = ModelGateway(SlowProvider(), timeout_seconds=0.1)

    with pytest.raises(ModelProviderTimeout):
        asyncio.run(gateway.generate(ModelGenerationRequest(prompt="timeout")))


def test_model_endpoint_remains_authenticated_by_default(tmp_path):
    app = create_app(str(tmp_path / "workspace.sqlite3"))
    client = TestClient(app, client=("127.0.0.1", 50000))

    response = client.post(
        "/v1/models/generate", json={"prompt": "must be protected"}
    )

    assert response.status_code == 401
