"""Provider-neutral, opt-in model gateway contracts for HUMANITY ONE.

No network provider is included. The default application has no configured provider.
"""
from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelGenerationRequest(BaseModel):
    """Bounded, transient prompt input. It is never persisted by this module."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    prompt: str = Field(min_length=1, max_length=20_000)
    system_instruction: str | None = Field(default=None, max_length=4_000)
    max_output_tokens: int = Field(default=512, ge=1, le=4_096)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    @field_validator("temperature")
    @classmethod
    def require_finite_temperature(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Temperature must be a finite number between 0 and 1")
        return value


class ModelUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class ProviderGeneration(BaseModel):
    """Provider output before gateway attribution and timestamping."""

    model_config = ConfigDict(extra="forbid")
    output: str = Field(min_length=1, max_length=100_000)
    usage: ModelUsage | None = None
    finish_reason: Literal["stop", "length", "content_filter", "unknown"] = "unknown"


class ModelGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    output: str = Field(min_length=1, max_length=100_000)
    usage: ModelUsage | None = None
    finish_reason: Literal["stop", "length", "content_filter", "unknown"]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("provider", "model")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Provider and model identifiers must not be blank")
        return normalized


class ModelProvider(Protocol):
    """An explicitly injected provider. Implementations must enforce their own limits."""

    provider_id: str
    model_id: str

    async def generate(self, request: ModelGenerationRequest) -> ProviderGeneration:
        """Generate output without persisting request or response content."""


class ModelGatewayError(Exception):
    """Base class for sanitized provider failures."""


class ModelProviderUnavailable(ModelGatewayError):
    pass


class ModelProviderFailure(ModelGatewayError):
    pass


class ModelProviderTimeout(ModelGatewayError):
    pass


class ModelGateway:
    """Executes one bounded request through an explicitly injected provider."""

    def __init__(
        self, provider: ModelProvider | None = None, *, timeout_seconds: float = 30.0
    ) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(
            timeout_seconds, (int, float)
        ):
            raise ValueError("Model gateway timeout must be a finite number between 0.1 and 120 seconds")
        timeout = float(timeout_seconds)
        if not math.isfinite(timeout) or not 0.1 <= timeout <= 120.0:
            raise ValueError("Model gateway timeout must be a finite number between 0.1 and 120 seconds")
        self.provider = provider
        self.timeout_seconds = timeout

    async def generate(self, request: ModelGenerationRequest) -> ModelGenerationResponse:
        if self.provider is None:
            raise ModelProviderUnavailable("No model provider is explicitly configured")
        try:
            result = await asyncio.wait_for(
                self.provider.generate(request), timeout=self.timeout_seconds
            )
            if not isinstance(result, ProviderGeneration):
                raise TypeError("Provider returned an invalid response contract")
            # Validate provider metadata and generated content inside the sanitized
            # boundary too. A faulty adapter must never turn a malformed result into
            # an unhandled API exception or leak its internal details.
            return ModelGenerationResponse(
                provider=self.provider.provider_id,
                model=self.provider.model_id,
                output=result.output,
                usage=result.usage,
                finish_reason=result.finish_reason,
            )
        except TimeoutError as exc:
            raise ModelProviderTimeout("Model provider request timed out") from exc
        except Exception as exc:
            raise ModelProviderFailure("Model provider request failed") from exc
