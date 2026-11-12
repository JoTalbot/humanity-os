"""Bounded source-lineage analysis without truth scoring or inferred independence."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from humanity_os.models import KnowledgeRecord
from humanity_os.store import KnowledgeStore


class IndependenceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    knowledge_ids: list[str] = Field(min_length=1, max_length=50)
    max_sources: int = Field(default=500, ge=1, le=500)

    @model_validator(mode="after")
    def unique_knowledge_ids(self) -> "IndependenceQuery":
        if len(self.knowledge_ids) != len(set(self.knowledge_ids)):
            raise ValueError("Knowledge IDs must be unique")
        return self


class SourceLineageItem(BaseModel):
    knowledge_id: str
    source_id: str
    canonical_uri: str
    publisher: str | None = None
    source_type: Literal["primary", "secondary", "unknown"]
    independence_group_id: str | None = None
    derived_from: list[str]
    lineage_roots: list[str]
    independence_status: Literal["declared_group", "derived_dependency", "unknown"]
    explanation: str


class IndependenceGroup(BaseModel):
    knowledge_id: str
    group_id: str
    source_keys: list[str]


class DependentSourceCluster(BaseModel):
    knowledge_id: str
    root_source_ids: list[str]
    member_source_ids: list[str]
    explanation: str


class EvidenceIndependenceReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    knowledge_ids: list[str]
    sources: list[SourceLineageItem]
    declared_groups: list[IndependenceGroup]
    dependent_clusters: list[DependentSourceCluster]
    unknown_lineage: list[str]
    limitations: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceIndependenceEngine:
    """Describes only explicitly recorded source groups and derivation edges."""

    def __init__(self, knowledge: KnowledgeStore) -> None:
        self.knowledge = knowledge

    def analyze(self, request: IndependenceQuery) -> EvidenceIndependenceReport:
        records: list[KnowledgeRecord] = []
        for knowledge_id in request.knowledge_ids:
            record = self.knowledge.get(knowledge_id)
            if record is None:
                raise LookupError(f"Knowledge record not found: {knowledge_id}")
            records.append(record)

        total = sum(len(record.sources) for record in records)
        if total > request.max_sources:
            raise ValueError(
                f"Source limit exceeded: {total} declared sources, limit is {request.max_sources}"
            )

        items: list[SourceLineageItem] = []
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        roots_by_record: dict[str, dict[str, set[str]]] = {}
        unknown: list[str] = []

        for record in records:
            source_map = {source.id: source for source in record.sources}
            memo: dict[str, set[str]] = {}

            def roots(source_id: str) -> set[str]:
                if source_id in memo:
                    return memo[source_id]
                source = source_map[source_id]
                parents = source.derived_from_source_ids
                result: set[str] = set()
                if not parents:
                    result.add(source_id)
                else:
                    for parent_id in parents:
                        result.update(roots(parent_id))
                memo[source_id] = result
                return result

            roots_by_record[record.id] = {}
            for source in record.sources:
                lineage_roots = sorted(roots(source.id))
                roots_by_record[record.id][source.id] = set(lineage_roots)
                if source.independence_group_id:
                    groups[(record.id, source.independence_group_id)].append(source.id)
                    status = "declared_group"
                    explanation = (
                        "Shares an explicitly declared independence group; this is a "
                        "recorded classification, not external verification."
                    )
                elif source.derived_from_source_ids:
                    status = "derived_dependency"
                    explanation = (
                        "Explicitly derives from one or more sources in this same "
                        "knowledge record; do not count it as independent corroboration."
                    )
                else:
                    status = "unknown"
                    explanation = (
                        "No independence group or derivation lineage is declared; "
                        "independence remains unknown."
                    )
                    unknown.append(f"{record.id}:{source.id}")
                items.append(SourceLineageItem(
                    knowledge_id=record.id,
                    source_id=source.id,
                    canonical_uri=source.canonical_uri or source.uri,
                    publisher=source.publisher,
                    source_type=source.source_type,
                    independence_group_id=source.independence_group_id,
                    derived_from=list(source.derived_from_source_ids),
                    lineage_roots=lineage_roots,
                    independence_status=status,
                    explanation=explanation,
                ))

        clusters: list[DependentSourceCluster] = []
        for record in records:
            by_root: dict[str, set[str]] = defaultdict(set)
            for source_id, root_ids in roots_by_record[record.id].items():
                for root_id in root_ids:
                    by_root[root_id].add(source_id)
            emitted: set[tuple[str, ...]] = set()
            for root_id, members in sorted(by_root.items()):
                if len(members) < 2 or root_id not in members:
                    continue
                signature = tuple(sorted(members))
                if signature in emitted:
                    continue
                emitted.add(signature)
                clusters.append(DependentSourceCluster(
                    knowledge_id=record.id,
                    root_source_ids=[root_id],
                    member_source_ids=list(signature),
                    explanation=(
                        "Multiple declared sources share this upstream source in their "
                        "recorded lineage; publication count is not independent evidence count."
                    ),
                ))

        declared_groups = [
            IndependenceGroup(
                knowledge_id=knowledge_id,
                group_id=group_id,
                source_keys=sorted(source_ids),
            )
            for (knowledge_id, group_id), source_ids in sorted(groups.items())
        ]
        return EvidenceIndependenceReport(
            knowledge_ids=list(request.knowledge_ids),
            sources=items,
            declared_groups=declared_groups,
            dependent_clusters=clusters,
            unknown_lineage=sorted(unknown),
            limitations=[
                "Source IDs and independence-group IDs are scoped to one knowledge record; identical IDs across records are not merged.",
                "A declared independence group is accepted as reviewer-provided metadata, not verified publisher independence.",
                "Different URLs, publishers, or content hashes do not establish independent origin.",
                "Unknown lineage remains unknown; the engine never assumes independence.",
                "Only declared derivation edges are traversed; missing upstream history cannot be reconstructed.",
                "This report describes provenance metadata and does not rank evidence, score truth, or adjudicate claims.",
                "Analysis is bounded to at most 50 knowledge records and 500 declared sources per request.",
            ],
        )
