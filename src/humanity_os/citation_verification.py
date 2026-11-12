"""Provenance-only validation for source citations in generated answer text."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from humanity_os.answer_context import AnswerContextSource
from humanity_os.documents import DocumentStore


class CitationValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=100_000)
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sources: list[AnswerContextSource] = Field(max_length=20)


class CitationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    citation_id: str
    status: Literal["verified", "unverified"]
    reason: Literal["not_in_manifest", "source_mismatch", "manifest_invalid"] | None = None


class CitationValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["verified", "unverified"]
    verification_scope: Literal["provenance_only"] = "provenance_only"
    semantic_support_verified: Literal[False] = False
    manifest_valid: bool
    citation_count: int
    checks: list[CitationCheck]
    reasons: list[Literal["no_citations", "manifest_digest_mismatch", "duplicate_manifest_id"]]


class CitationValidator:
    """Checks citation identity and source integrity, never semantic entailment."""

    _citation_pattern = re.compile(r"\[(src-[^\]\s]+)\]")

    def __init__(self, documents: DocumentStore) -> None:
        self.documents = documents

    @staticmethod
    def _manifest_digest(sources: list[AnswerContextSource]) -> str:
        manifest = [source.model_dump(mode="json") for source in sources]
        canonical = json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def validate(self, request: CitationValidationRequest) -> CitationValidationResponse:
        citation_ids = list(dict.fromkeys(self._citation_pattern.findall(request.answer)))
        source_by_id: dict[str, AnswerContextSource] = {}
        duplicate_manifest_ids = False
        for source in request.sources:
            if source.citation_id in source_by_id:
                duplicate_manifest_ids = True
            source_by_id[source.citation_id] = source
        digest_valid = self._manifest_digest(request.sources) == request.manifest_sha256
        manifest_valid = digest_valid and not duplicate_manifest_ids
        reasons: list[str] = []
        if not citation_ids:
            reasons.append("no_citations")
        if not digest_valid:
            reasons.append("manifest_digest_mismatch")
        if duplicate_manifest_ids:
            reasons.append("duplicate_manifest_id")
        checks = []
        for citation_id in citation_ids:
            source = source_by_id.get(citation_id)
            if not manifest_valid:
                checks.append(CitationCheck(
                    citation_id=citation_id, status="unverified", reason="manifest_invalid"
                ))
            elif source is None:
                checks.append(CitationCheck(
                    citation_id=citation_id, status="unverified", reason="not_in_manifest"
                ))
            elif not self.documents.verify_source(source.model_dump(mode="python")):
                checks.append(CitationCheck(
                    citation_id=citation_id, status="unverified", reason="source_mismatch"
                ))
            else:
                checks.append(CitationCheck(citation_id=citation_id, status="verified"))
        status = "verified" if checks and all(item.status == "verified" for item in checks) else "unverified"
        return CitationValidationResponse(
            status=status,
            manifest_valid=manifest_valid,
            citation_count=len(citation_ids),
            checks=checks,
            reasons=reasons,
        )