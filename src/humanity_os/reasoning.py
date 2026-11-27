"""Bounded, provenance-aware and explainable knowledge graph traversal."""
from __future__ import annotations

import sqlite3
from collections import deque
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from humanity_os.claim_assessments import ClaimAssessmentStore
from humanity_os.claim_graph import ClaimGraphStore
from humanity_os.evidence import EvidenceAssessmentStore
from humanity_os.independence import (
    EvidenceIndependenceEngine,
    EvidenceIndependenceReport,
    IndependenceQuery,
)
from humanity_os.models import ClaimAssessment, ClaimNode, ClaimRelation, EvidenceAssessment
from humanity_os.store import KnowledgeStore


class ReasoningQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4_000)
    root_claim_id: str = Field(min_length=1, max_length=128)
    max_depth: int = Field(default=3, ge=0, le=5)
    max_nodes: int = Field(default=30, ge=1, le=50)
    scope: str | None = Field(default=None, max_length=2_000)
    temporal_scope: str | None = Field(default=None, max_length=500)


class EvidenceReference(BaseModel):
    knowledge_id: str
    evidence_id: str
    evidence_relation: str
    source_id: str
    source_uri: str
    source_title: str | None = None
    publisher: str | None = None
    content_hash: str | None = None
    source_type: str = "unknown"
    independence_group_id: str | None = None
    derived_from_source_ids: list[str] = Field(default_factory=list)
    assessments: list[EvidenceAssessment] = Field(default_factory=list)
    excerpt: str | None = None
    locator: str | None = None


class PotentialContradiction(BaseModel):
    left_claim_id: str
    right_claim_id: str
    matched_subject: str
    matched_predicate: str
    matched_object: str
    scope: str | None = None
    temporal_scope: str | None = None
    modality: str
    left_polarity: Literal["affirmed", "negated"]
    right_polarity: Literal["affirmed", "negated"]
    basis: Literal["exact_structured_match_opposite_polarity"] = (
        "exact_structured_match_opposite_polarity"
    )


class TemporalClaimDifference(BaseModel):
    left_claim_id: str
    right_claim_id: str
    matched_subject: str
    matched_predicate: str
    matched_object: str
    scope: str | None = None
    modality: str
    left_temporal_scope: str
    right_temporal_scope: str
    polarity_relation: Literal["same", "opposite"]
    basis: Literal["same_structured_proposition_distinct_time_labels"] = (
        "same_structured_proposition_distinct_time_labels"
    )


class DeclaredDependencyPath(BaseModel):
    claim_ids: list[str]
    relation_ids: list[str]
    basis: Literal["explicit_depends_on_edges"] = "explicit_depends_on_edges"


class ReasoningRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    root_claim_id: str
    max_depth: int
    max_nodes: int
    scope_filter: str | None = None
    temporal_scope_filter: str | None = None
    claims: list[ClaimNode]
    relations: list[ClaimRelation]
    claim_assessments: list[ClaimAssessment]
    paths: list[list[str]]
    declared_dependency_paths: list[DeclaredDependencyPath] = Field(default_factory=list)
    evidence: list[EvidenceReference]
    evidence_independence: EvidenceIndependenceReport | None = None
    contradiction_candidates: list[str]
    potential_contradictions: list[PotentialContradiction] = Field(default_factory=list)
    temporal_claim_differences: list[TemporalClaimDifference] = Field(default_factory=list)
    limitations: list[str]
    actor: Literal["owner", "system"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReasoningComparisonQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4_000)
    root_claim_ids: list[str] = Field(min_length=2, max_length=10)
    max_depth: int = Field(default=3, ge=0, le=5)
    max_nodes: int = Field(default=30, ge=1, le=50)
    scope: str | None = Field(default=None, max_length=2_000)
    temporal_scope: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_unique_roots(self) -> ReasoningComparisonQuery:
        if len(self.root_claim_ids) != len(set(self.root_claim_ids)):
            raise ValueError("Comparison root claim IDs must be unique")
        return self


class HypothesisEvidenceProfile(BaseModel):
    root_claim_id: str
    claim_count: int
    claim_classifications: dict[str, int]
    evidence_link_count: int
    evidence_stance_counts: dict[str, int]
    evidence_review_status_counts: dict[str, int]
    assessed_evidence_link_count: int
    review_required_evidence_link_count: int
    unassessed_evidence_link_count: int
    distinct_source_count: int
    declared_independence_group_count: int
    dependent_source_edge_count: int
    unknown_lineage_source_count: int


class HypothesisClaimCoverageReference(BaseModel):
    root_claim_id: str
    claim_ids: list[str] = Field(default_factory=list, max_length=50)


class HypothesisClaimCoverageGap(BaseModel):
    target_root_claim_id: str
    subject: str
    predicate: str
    object: str
    scope: str | None = None
    modality: str
    temporal_scope: str | None = None
    represented_in: list[HypothesisClaimCoverageReference] = Field(
        default_factory=list, max_length=9
    )
    basis: Literal[
        "peer_hypothesis_structured_claim_not_present_in_target_bounded_traversal"
    ] = "peer_hypothesis_structured_claim_not_present_in_target_bounded_traversal"


class ReasoningComparison(BaseModel):
    query: str
    runs: list[ReasoningRun]
    shared_claim_ids: list[str]
    unique_claim_ids: dict[str, list[str]]
    shared_source_uris: list[str]
    unique_source_uris: dict[str, list[str]]
    shared_independence_groups: list[str] = Field(default_factory=list)
    unique_independence_groups: dict[str, list[str]] = Field(default_factory=dict)
    evidence_profiles: dict[str, HypothesisEvidenceProfile] = Field(default_factory=dict)
    shared_evidence_ids: list[str] = Field(default_factory=list)
    unique_evidence_ids: dict[str, list[str]] = Field(default_factory=dict)
    claim_coverage_gaps: list[HypothesisClaimCoverageGap] = Field(default_factory=list, max_length=500)
    dependent_source_edges: list[str] = Field(default_factory=list)
    unknown_lineage_sources: list[str] = Field(default_factory=list)
    limitations: list[str]
    actor: Literal["owner", "system"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReasoningEngine:
    """Creates bounded explanations; it does not infer truth or adjudicate disputes."""

    def __init__(
        self,
        database_path: str | Path,
        knowledge: KnowledgeStore,
        graph: ClaimGraphStore,
        evidence_assessments: EvidenceAssessmentStore | None = None,
    ) -> None:
        self.database_path = str(database_path)
        self.knowledge = knowledge
        self.graph = graph
        self.assessments = ClaimAssessmentStore(self.database_path)
        self.evidence_assessments = evidence_assessments or EvidenceAssessmentStore(self.database_path)
        self.independence = EvidenceIndependenceEngine(knowledge)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS reasoning_runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reasoning_runs_created "
                "ON reasoning_runs(created_at DESC, id DESC)"
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS reasoning_runs_no_update
                   BEFORE UPDATE ON reasoning_runs
                   BEGIN SELECT RAISE(ABORT, 'reasoning runs are append-only'); END"""
            )
            connection.execute(
                """CREATE TRIGGER IF NOT EXISTS reasoning_runs_no_delete
                   BEFORE DELETE ON reasoning_runs
                   BEGIN SELECT RAISE(ABORT, 'reasoning runs are append-only'); END"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _matches(claim: ClaimNode, request: ReasoningQuery) -> bool:
        if request.scope is not None and claim.scope != request.scope:
            return False
        return request.temporal_scope is None or claim.temporal_scope == request.temporal_scope

    def run(self, request: ReasoningQuery, actor: str) -> ReasoningRun:
        root = self.graph.get_claim(request.root_claim_id)
        if root is None:
            raise LookupError("Root claim not found")
        if not self._matches(root, request):
            raise ValueError("Root claim does not match the requested scope and temporal filters")

        # Fetch only the bounded neighborhood of each visited node. A global
        # "latest 100" graph slice silently hid older roots and their edges.
        selected: dict[str, ClaimNode] = {root.id: root}
        paths: list[list[str]] = [[root.id]]
        selected_relations: dict[str, ClaimRelation] = {}
        relation_limit_hit = False
        queue = deque([(root.id, 0, [root.id])])
        while queue and len(selected) < request.max_nodes:
            current_id, depth, path = queue.popleft()
            if depth >= request.max_depth:
                continue
            edges = self.graph.list_relations(claim_id=current_id, limit=100)
            relation_limit_hit = relation_limit_hit or len(edges) == 100
            for edge in edges:
                if edge.relation in {"contradicts", "duplicates"}:
                    # Symmetric relations can be traversed from either endpoint.
                    next_id = (
                        edge.target_claim_id
                        if edge.source_claim_id == current_id
                        else edge.source_claim_id
                    )
                elif edge.source_claim_id == current_id:
                    # All other relation types are directed. Incoming edges
                    # must not leak into the result without their source node.
                    next_id = edge.target_claim_id
                else:
                    continue
                candidate = selected.get(next_id)
                if candidate is None:
                    candidate = self.graph.get_claim(next_id)
                if candidate is None or not self._matches(candidate, request):
                    continue
                selected_relations[edge.id] = edge
                if next_id in selected:
                    continue
                selected[next_id] = candidate
                next_path = [*path, next_id]
                paths.append(next_path)
                queue.append((next_id, depth + 1, next_path))
                if len(selected) >= request.max_nodes:
                    break

        evidence: list[EvidenceReference] = []
        assessment_cache: dict[str, list[EvidenceAssessment]] = {}
        for claim in selected.values():
            record = self.knowledge.get(claim.knowledge_id)
            if record is None:
                continue
            source_by_id = {source.id: source for source in record.sources}
            evidence_by_id = {item.id: item for item in record.evidence}
            if record.id not in assessment_cache:
                assessment_cache[record.id] = self.evidence_assessments.latest_for_knowledge(record.id)
            assessments_by_key = {
                (item.source_id, item.evidence_id): item
                for item in assessment_cache[record.id]
            }
            for evidence_id in claim.evidence_ids:
                item = evidence_by_id.get(evidence_id)
                source = source_by_id.get(item.source_id) if item else None
                if item is None or source is None:
                    continue
                linked_assessments = [
                    assessments_by_key[key]
                    for key in ((source.id, item.id), (source.id, None))
                    if key in assessments_by_key
                ]
                evidence.append(EvidenceReference(
                    knowledge_id=record.id,
                    evidence_id=item.id,
                    evidence_relation=item.relation,
                    source_id=source.id,
                    source_uri=source.canonical_uri or source.uri,
                    source_title=source.title,
                    publisher=source.publisher,
                    content_hash=source.content_hash,
                    source_type=source.source_type,
                    independence_group_id=source.independence_group_id,
                    derived_from_source_ids=list(source.derived_from_source_ids),
                    assessments=linked_assessments,
                    excerpt=item.excerpt,
                    locator=item.locator,
                ))

        contradictions = sorted(
            edge.id for edge in selected_relations.values()
            if edge.relation == "contradicts"
            and edge.source_claim_id in selected
            and edge.target_claim_id in selected
        )
        potential_contradictions: list[PotentialContradiction] = []
        temporal_claim_differences: list[TemporalClaimDifference] = []
        selected_claims = list(selected.values())
        for index, left in enumerate(selected_claims):
            if left.polarity not in {"affirmed", "negated"}:
                continue
            left_terms = (left.subject, left.predicate, left.object)
            if any(not value or not value.strip() for value in left_terms):
                continue
            for right in selected_claims[index + 1:]:
                if right.polarity not in {"affirmed", "negated"}:
                    continue
                if left.scope != right.scope or left.modality != right.modality:
                    continue
                right_terms = (right.subject, right.predicate, right.object)
                if any(not value or not value.strip() for value in right_terms):
                    continue
                normalized_left = tuple(
                    " ".join(value.casefold().split()) for value in left_terms
                )
                normalized_right = tuple(
                    " ".join(value.casefold().split()) for value in right_terms
                )
                if normalized_left != normalized_right:
                    continue
                if left.temporal_scope and right.temporal_scope and (
                    left.temporal_scope != right.temporal_scope
                ):
                    temporal_claim_differences.append(TemporalClaimDifference(
                        left_claim_id=left.id,
                        right_claim_id=right.id,
                        matched_subject=left.subject or "",
                        matched_predicate=left.predicate or "",
                        matched_object=left.object or "",
                        scope=left.scope,
                        modality=left.modality,
                        left_temporal_scope=left.temporal_scope,
                        right_temporal_scope=right.temporal_scope,
                        polarity_relation=(
                            "same" if left.polarity == right.polarity else "opposite"
                        ),
                    ))
                    continue
                if right.polarity == left.polarity:
                    continue
                potential_contradictions.append(PotentialContradiction(
                    left_claim_id=left.id,
                    right_claim_id=right.id,
                    matched_subject=left.subject or "",
                    matched_predicate=left.predicate or "",
                    matched_object=left.object or "",
                    scope=left.scope,
                    temporal_scope=left.temporal_scope,
                    modality=left.modality,
                    left_polarity=left.polarity,
                    right_polarity=right.polarity,
                ))

        declared_dependency_paths: list[DeclaredDependencyPath] = []
        for path in paths:
            relation_ids: list[str] = []
            for source_id, target_id in pairwise(path):
                dependency = next(
                    (
                        edge for edge in selected_relations.values()
                        if edge.relation == "depends_on"
                        and edge.source_claim_id == source_id
                        and edge.target_claim_id == target_id
                    ),
                    None,
                )
                if dependency is None:
                    break
                relation_ids.append(dependency.id)
            else:
                if relation_ids:
                    declared_dependency_paths.append(DeclaredDependencyPath(
                        claim_ids=path,
                        relation_ids=relation_ids,
                    ))

        knowledge_ids = sorted({claim.knowledge_id for claim in selected.values()})
        independence_report = None
        independence_limit_hit = False
        if knowledge_ids:
            try:
                independence_report = self.independence.analyze(
                    IndependenceQuery(knowledge_ids=knowledge_ids, max_sources=500)
                )
            except ValueError:
                # Keep the reasoning result available, but never silently imply
                # source independence when the bounded lineage analysis is incomplete.
                independence_limit_hit = True
        limitations = [
            "This is a graph explanation, not a proof of truth.",
            "Claim and relation records are human-authored assertions; no truth score is calculated.",
            "Epistemic classifications are human assessments; absence of a classification is not an unknown verdict.",
            "Only declared evidence links are shown; external sources are not fetched or authenticated.",
            "Potential contradictions are exact structured-field matches with opposite polarity, not semantic contradiction judgments.",
            "Temporal claim differences only report distinct non-empty time labels; interval overlap and chronological ordering are not inferred.",
            "Declared dependency paths contain only explicit depends_on edges; they do not establish causation.",
            "Scope and temporal filters use exact string matching, not interval or ontology reasoning.",
            "Each visited claim neighborhood is bounded to 100 directly linked relations; traversal also obeys the requested depth and node limits.",
        ]
        if len(selected) >= request.max_nodes:
            limitations.append("The requested node limit was reached; additional connected claims may exist.")
        if relation_limit_hit:
            limitations.append("At least one visited claim has 100 or more directly linked relations; additional edges may be omitted.")
        if independence_limit_hit:
            limitations.append(
                "Source-lineage analysis exceeded its 500-source bound; independence remains unassessed."
            )


        result = ReasoningRun(
            query=request.query,
            root_claim_id=root.id,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            scope_filter=request.scope,
            temporal_scope_filter=request.temporal_scope,
            claims=list(selected.values()),
            relations=list(selected_relations.values()),
            claim_assessments=self.assessments.latest_for_claims(list(selected)),
            paths=paths,
            declared_dependency_paths=declared_dependency_paths,
            evidence=evidence,
            evidence_independence=independence_report,
            contradiction_candidates=contradictions,
            potential_contradictions=potential_contradictions,
            temporal_claim_differences=temporal_claim_differences,
            limitations=limitations,
            actor=actor,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO reasoning_runs(id, created_at, payload) VALUES (?, ?, ?)",
                (result.id, result.created_at.isoformat(), result.model_dump_json()),
            )
        return result


    def compare(
        self, request: ReasoningComparisonQuery, actor: str
    ) -> ReasoningComparison:
        roots = []
        for claim_id in request.root_claim_ids:
            claim = self.graph.get_claim(claim_id)
            if claim is None:
                raise LookupError(f"Root claim not found: {claim_id}")
            query = ReasoningQuery(
                query=request.query,
                root_claim_id=claim_id,
                max_depth=request.max_depth,
                max_nodes=request.max_nodes,
                scope=request.scope,
                temporal_scope=request.temporal_scope,
            )
            if not self._matches(claim, query):
                raise ValueError(f"Root claim does not match requested filters: {claim_id}")
            roots.append(claim)

        runs = [
            self.run(
                ReasoningQuery(
                    query=request.query,
                    root_claim_id=claim.id,
                    max_depth=request.max_depth,
                    max_nodes=request.max_nodes,
                    scope=request.scope,
                    temporal_scope=request.temporal_scope,
                ),
                actor=actor,
            )
            for claim in roots
        ]
        claim_sets = {run.root_claim_id: {claim.id for claim in run.claims} for run in runs}
        source_sets = {
            run.root_claim_id: {item.source_uri for item in run.evidence}
            for run in runs
        }
        group_sets = {
            run.root_claim_id: {
                f"{item.knowledge_id}:{item.independence_group_id}"
                for item in run.evidence
                if item.independence_group_id
            }
            for run in runs
        }
        evidence_sets = {
            run.root_claim_id: {
                f"{item.knowledge_id}:{item.evidence_id}"
                for item in run.evidence
            }
            for run in runs
        }
        profiles: dict[str, HypothesisEvidenceProfile] = {}
        for run in runs:
            classifications: dict[str, int] = {}
            for assessment in run.claim_assessments:
                classifications[assessment.classification] = (
                    classifications.get(assessment.classification, 0) + 1
                )
            stances: dict[str, int] = {}
            statuses: dict[str, int] = {}
            assessed_links = 0
            review_required_links = 0
            unique_evidence = {
                (item.knowledge_id, item.evidence_id): item
                for item in run.evidence
            }
            unique_sources = {
                (item.knowledge_id, item.source_id): item
                for item in unique_evidence.values()
            }
            dependency_edges = {
                (item.knowledge_id, item.source_id, parent_id)
                for item in unique_sources.values()
                for parent_id in item.derived_from_source_ids
            }
            unknown_sources = {
                (item.knowledge_id, item.source_id)
                for item in unique_sources.values()
                if not item.independence_group_id and not item.derived_from_source_ids
            }
            for item in unique_evidence.values():
                specific = next(
                    (entry for entry in item.assessments if entry.evidence_id is not None),
                    None,
                )
                assessment = specific or (item.assessments[0] if item.assessments else None)
                if assessment is None:
                    statuses["unassessed"] = statuses.get("unassessed", 0) + 1
                    continue
                if assessment.status == "assessed":
                    assessed_links += 1
                else:
                    review_required_links += 1
                stances[assessment.stance] = stances.get(assessment.stance, 0) + 1
                statuses[assessment.status] = statuses.get(assessment.status, 0) + 1
            profiles[run.root_claim_id] = HypothesisEvidenceProfile(
                root_claim_id=run.root_claim_id,
                claim_count=len(run.claims),
                claim_classifications=classifications,
                evidence_link_count=len(unique_evidence),
                evidence_stance_counts=stances,
                evidence_review_status_counts=statuses,
                assessed_evidence_link_count=assessed_links,
                review_required_evidence_link_count=review_required_links,
                unassessed_evidence_link_count=(
                    len(unique_evidence) - assessed_links - review_required_links
                ),
                distinct_source_count=len(unique_sources),
                declared_independence_group_count=len({
                    (item.knowledge_id, item.independence_group_id)
                    for item in unique_sources.values()
                    if item.independence_group_id
                }),
                dependent_source_edge_count=len(dependency_edges),
                unknown_lineage_source_count=len(unknown_sources),
            )
        # Report only structured-claim coverage differences observed in these
        # bounded traversals. A gap is not a claim that evidence should exist.
        structured_claims: dict[str, dict[tuple[str, str, str, str | None, str, str | None], list[ClaimNode]]] = {}
        for run in runs:
            by_key: dict[tuple[str, str, str, str | None, str, str | None], list[ClaimNode]] = {}
            for claim in run.claims:
                terms = (claim.subject, claim.predicate, claim.object)
                if any(not value or not value.strip() for value in terms):
                    continue
                key = (
                    " ".join((claim.subject or "").casefold().split()),
                    " ".join((claim.predicate or "").casefold().split()),
                    " ".join((claim.object or "").casefold().split()),
                    " ".join(claim.scope.casefold().split()) if claim.scope else None,
                    claim.modality,
                    " ".join(claim.temporal_scope.casefold().split()) if claim.temporal_scope else None,
                )
                by_key.setdefault(key, []).append(claim)
            structured_claims[run.root_claim_id] = by_key

        all_propositions = set().union(
            *(set(items) for items in structured_claims.values())
        )
        coverage_gaps: list[HypothesisClaimCoverageGap] = []
        for target_root_id in sorted(structured_claims):
            target_keys = structured_claims[target_root_id]
            for key in sorted(all_propositions - set(target_keys), key=repr):
                represented_in = [
                    HypothesisClaimCoverageReference(
                        root_claim_id=peer_root_id,
                        claim_ids=sorted({claim.id for claim in peer_claims[key]}),
                    )
                    for peer_root_id, peer_claims in sorted(structured_claims.items())
                    if peer_root_id != target_root_id and key in peer_claims
                ]
                if not represented_in:
                    continue
                subject, predicate, object_value, scope, modality, temporal_scope = key
                coverage_gaps.append(HypothesisClaimCoverageGap(
                    target_root_claim_id=target_root_id,
                    subject=subject,
                    predicate=predicate,
                    object=object_value,
                    scope=scope,
                    modality=modality,
                    temporal_scope=temporal_scope,
                    represented_in=represented_in,
                ))
                if len(coverage_gaps) >= 500:
                    break
            if len(coverage_gaps) >= 500:
                break

        dependent_edges = sorted({
            f"{item.knowledge_id}:{item.source_id}<-{parent_id}"
            for run in runs
            for item in run.evidence
            for parent_id in item.derived_from_source_ids
        })
        unknown_lineage = sorted({
            f"{item.knowledge_id}:{item.source_id}"
            for run in runs
            for item in run.evidence
            if not item.independence_group_id and not item.derived_from_source_ids
        })
        shared_claims = set.intersection(*claim_sets.values())
        shared_sources = set.intersection(*source_sets.values())
        shared_groups = set.intersection(*group_sets.values())
        shared_evidence = set.intersection(*evidence_sets.values())
        return ReasoningComparison(
            query=request.query,
            runs=runs,
            shared_claim_ids=sorted(shared_claims),
            unique_claim_ids={
                root_id: sorted(values - shared_claims)
                for root_id, values in claim_sets.items()
            },
            shared_source_uris=sorted(shared_sources),
            unique_source_uris={
                root_id: sorted(values - shared_sources)
                for root_id, values in source_sets.items()
            },
            shared_independence_groups=sorted(shared_groups),
            unique_independence_groups={
                root_id: sorted(values - shared_groups)
                for root_id, values in group_sets.items()
            },
            evidence_profiles=profiles,
            shared_evidence_ids=sorted(shared_evidence),
            unique_evidence_ids={
                root_id: sorted(values - shared_evidence)
                for root_id, values in evidence_sets.items()
            },
            claim_coverage_gaps=coverage_gaps,
            dependent_source_edges=dependent_edges,
            unknown_lineage_sources=unknown_lineage,
            limitations=[
                "Comparison is set overlap across bounded graph traversals, not a ranking of hypotheses.",
                "Shared claims or sources do not establish correctness or independent corroboration.",
                "Independence groups are reviewer-declared and scoped to parent knowledge records; unknown lineage remains unknown.",
                "Derived-source edges indicate recorded dependency, not verified copying or publisher identity.",
                "Each alternative is stored as its own immutable reasoning run.",
                "Claim coverage gaps report structured propositions absent from a bounded traversal; they do not establish missing evidence, relevance, or falsity.",
            ],
            actor=actor,
        )

    def get(self, run_id: str) -> ReasoningRun | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM reasoning_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return ReasoningRun.model_validate_json(row["payload"]) if row else None

    @staticmethod
    def verify_rows(rows: list[tuple[str]]) -> None:
        for (payload,) in rows:
            ReasoningRun.model_validate_json(payload)
