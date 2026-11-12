"""Versioned API models for the personal knowledge core."""
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

Visibility = Literal["private", "shared", "public"]
KnowledgeKind = Literal["claim", "concept", "procedure", "observation", "hypothesis", "question", "dataset", "document"]

def utc_now() -> datetime:
    return datetime.now(UTC)

class KnowledgeSource(BaseModel):
    """A durable source identity with explicit provenance lineage."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    uri: str = Field(min_length=1, max_length=2_048)
    title: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=300)
    published_at: datetime | None = None
    accessed_at: datetime | None = None
    content_hash: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    source_type: Literal["primary", "secondary", "unknown"] = "unknown"
    independence_group_id: str | None = Field(default=None, min_length=1, max_length=128)
    derived_from_source_ids: list[str] = Field(default_factory=list, max_length=100)
    canonical_uri: str | None = Field(default=None, max_length=2_048)

    @model_validator(mode="after")
    def normalize_canonical_uri(self) -> "KnowledgeSource":
        from urllib.parse import urlsplit, urlunsplit

        original = self.uri.strip()
        parts = urlsplit(original)
        normalized = original
        if parts.scheme.lower() in {"http", "https"} and parts.netloc:
            if not (parts.username or parts.password):
                host = (parts.hostname or "").lower()
                if ":" in host:
                    host = f"[{host}]"
                port = parts.port
                netloc = host
                if port and not (
                    (parts.scheme.lower() == "http" and port == 80)
                    or (parts.scheme.lower() == "https" and port == 443)
                ):
                    netloc = f"{host}:{port}"
                path = parts.path or "/"
                if path != "/":
                    path = path.rstrip("/")
                normalized = urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))
        if self.canonical_uri is not None and self.canonical_uri != normalized:
            raise ValueError("Canonical URI must match the normalized source URI")
        self.canonical_uri = normalized
        return self



class EvidenceLink(BaseModel):
    """A bounded relation between a knowledge record and one declared source."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    relation: Literal["supports", "refutes", "mentions", "context"]
    excerpt: str | None = Field(default=None, max_length=4_000)
    locator: str | None = Field(default=None, max_length=500)


class KnowledgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: KnowledgeKind
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=200_000)
    language: str = Field(default="und", min_length=2, max_length=35)
    visibility: Visibility = "private"
    source_uri: str | None = Field(default=None, max_length=2_048)
    sources: list[KnowledgeSource] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceLink] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_evidence_sources(self) -> "KnowledgeCreate":
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Knowledge source IDs must be unique")
        evidence_ids = [item.id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence IDs must be unique")
        declared = set(source_ids)
        missing = sorted({item.source_id for item in self.evidence} - declared)
        if missing:
            raise ValueError("Evidence references an undeclared source ID")
        source_by_id = {source.id: source for source in self.sources}
        canonical_uris = [source.canonical_uri for source in self.sources]
        if len(canonical_uris) != len(set(canonical_uris)):
            raise ValueError("Canonical source URIs must be unique within a knowledge record")
        for source in self.sources:
            if len(source.derived_from_source_ids) != len(set(source.derived_from_source_ids)):
                raise ValueError("Derived source references must be unique")
            if source.id in source.derived_from_source_ids:
                raise ValueError("A source cannot derive from itself")
            if set(source.derived_from_source_ids) - declared:
                raise ValueError("Derived source references must point to declared sources")
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(source_id: str) -> None:
            if source_id in visiting:
                raise ValueError("Source derivation lineage cannot contain cycles")
            if source_id in visited:
                return
            visiting.add(source_id)
            for parent_id in source_by_id[source_id].derived_from_source_ids:
                visit(parent_id)
            visiting.remove(source_id)
            visited.add(source_id)
        for source_id in declared:
            visit(source_id)
        return self

class KnowledgeRecord(KnowledgeCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = "0.1"
    revision: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class KnowledgeRevision(BaseModel):
    """Immutable snapshot metadata and the complete record state at one revision."""
    record_id: str
    revision: int = Field(ge=1)
    actor: Literal["owner", "system"]
    change_reason: str = Field(min_length=1, max_length=2_000)
    created_at: datetime
    snapshot: "KnowledgeRecord"


class KnowledgeList(BaseModel):
    items: list[KnowledgeRecord]
    next_cursor: str | None = None


ConflictStatus = Literal["pending_review", "resolved", "dismissed"]


class ConflictCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_a_id: str = Field(min_length=1, max_length=128)
    record_b_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=4_000)

    @model_validator(mode="after")
    def validate_distinct_records(self) -> "ConflictCreate":
        if self.record_a_id == self.record_b_id:
            raise ValueError("A knowledge record cannot conflict with itself")
        return self


class ConflictDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["resolved", "dismissed"]
    resolution_note: str = Field(min_length=1, max_length=4_000)


class KnowledgeConflict(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    record_a_id: str
    record_b_id: str
    reason: str
    status: ConflictStatus = "pending_review"
    resolution_note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


DecisionAction = Literal["made", "reaffirmed", "reversed", "superseded"]


class DecisionCreate(BaseModel):
    """A human-accountable decision with explicit alternatives and rationale."""
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    question: str = Field(min_length=1, max_length=4_000)
    context: str = Field(min_length=1, max_length=8_000)
    alternatives: list[str] = Field(min_length=2, max_length=50)
    selected_option: str = Field(min_length=1, max_length=4_000)
    rationale: str = Field(min_length=1, max_length=8_000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    related_knowledge_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_alternatives(self) -> "DecisionCreate":
        normalized = [item.strip() for item in self.alternatives]
        if any(not item for item in normalized):
            raise ValueError("Decision alternatives cannot be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Decision alternatives must be unique")
        if self.selected_option not in normalized:
            raise ValueError("Selected option must be one of the declared alternatives")
        if len(self.related_knowledge_ids) != len(set(self.related_knowledge_ids)):
            raise ValueError("Related knowledge IDs must be unique")
        return self


class DecisionRecord(DecisionCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    actor: Literal["owner", "system"]
    action: DecisionAction = "made"
    supersedes_decision_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


EvidenceAssessmentStance = Literal["supports", "refutes", "neutral"]
EvidenceAssessmentStatus = Literal["unassessed", "assessed", "review_required"]
EvidenceAssessmentMethod = Literal["manual", "document_review", "cross_check", "automated_triage"]


class EvidenceAssessmentCreate(BaseModel):
    """A recorded assessment of one declared source/evidence relationship."""
    model_config = ConfigDict(extra="forbid")
    knowledge_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    evidence_id: str | None = Field(default=None, min_length=1, max_length=128)
    stance: EvidenceAssessmentStance
    status: Literal["assessed", "review_required"]
    method: EvidenceAssessmentMethod
    notes: str = Field(min_length=1, max_length=4_000)


class EvidenceAssessment(EvidenceAssessmentCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    actor: Literal["owner", "system"]
    assessed_at: datetime = Field(default_factory=utc_now)
