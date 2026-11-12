"""Bounded, provenance-aware and explainable knowledge graph traversal."""
from __future__ import annotations

import sqlite3
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from humanity_os.claim_graph import ClaimGraphStore
from humanity_os.models import ClaimNode, ClaimRelation
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
    excerpt: str | None = None
    locator: str | None = None


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
    paths: list[list[str]]
    evidence: list[EvidenceReference]
    contradiction_candidates: list[str]
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
    ) -> None:
        self.database_path = str(database_path)
        self.knowledge = knowledge
        self.graph = graph
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
        if request.temporal_scope is not None and claim.temporal_scope != request.temporal_scope:
            return False
        return True

    def run(self, request: ReasoningQuery, actor: str) -> ReasoningRun:
        root = self.graph.get_claim(request.root_claim_id)
        if root is None:
            raise LookupError("Root claim not found")
        if not self._matches(root, request):
            raise ValueError("Root claim does not match the requested scope and temporal filters")

        # Existing list APIs are deliberately bounded; the run never scans an unbounded graph.
        all_claims = self.graph.list_claims(limit=100)
        claim_by_id = {claim.id: claim for claim in all_claims}
        claim_by_id[root.id] = root
        all_relations = self.graph.list_relations(limit=100)
        adjacency: dict[str, list[ClaimRelation]] = {}
        for relation in all_relations:
            adjacency.setdefault(relation.source_claim_id, []).append(relation)
            if relation.relation in {"contradicts", "duplicates"}:
                adjacency.setdefault(relation.target_claim_id, []).append(relation)

        selected: dict[str, ClaimNode] = {root.id: root}
        paths: list[list[str]] = [[root.id]]
        selected_relations: dict[str, ClaimRelation] = {}
        queue = deque([(root.id, 0, [root.id])])
        while queue and len(selected) < request.max_nodes:
            current_id, depth, path = queue.popleft()
            if depth >= request.max_depth:
                continue
            for edge in adjacency.get(current_id, []):
                if edge.relation in {"contradicts", "duplicates"} and edge.source_claim_id == current_id:
                    next_id = edge.target_claim_id
                elif edge.relation in {"contradicts", "duplicates"} and edge.target_claim_id == current_id:
                    next_id = edge.source_claim_id
                else:
                    next_id = edge.target_claim_id
                candidate = claim_by_id.get(next_id)
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
        for claim in selected.values():
            record = self.knowledge.get(claim.knowledge_id)
            if record is None:
                continue
            source_by_id = {source.id: source for source in record.sources}
            evidence_by_id = {item.id: item for item in record.evidence}
            for evidence_id in claim.evidence_ids:
                item = evidence_by_id.get(evidence_id)
                source = source_by_id.get(item.source_id) if item else None
                if item is None or source is None:
                    continue
                evidence.append(EvidenceReference(
                    knowledge_id=record.id,
                    evidence_id=item.id,
                    evidence_relation=item.relation,
                    source_id=source.id,
                    source_uri=source.canonical_uri or source.uri,
                    source_title=source.title,
                    publisher=source.publisher,
                    content_hash=source.content_hash,
                    excerpt=item.excerpt,
                    locator=item.locator,
                ))

        contradictions = sorted(
            edge.id for edge in selected_relations.values()
            if edge.relation == "contradicts"
            and edge.source_claim_id in selected
            and edge.target_claim_id in selected
        )
        limitations = [
            "This is a graph explanation, not a proof of truth.",
            "Claim and relation records are human-authored assertions; no truth score is calculated.",
            "Only declared evidence links are shown; external sources are not fetched or authenticated.",
            "Scope and temporal filters use exact string matching, not interval or ontology reasoning.",
            "The graph snapshot is bounded to at most 100 claims and 100 relations.",
        ]
        if len(selected) >= request.max_nodes:
            limitations.append("The requested node limit was reached; additional connected claims may exist.")
        if len(all_claims) >= 100 or len(all_relations) >= 100:
            limitations.append("The stored graph exceeds the traversal snapshot cap; results may be incomplete.")

        result = ReasoningRun(
            query=request.query,
            root_claim_id=root.id,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            scope_filter=request.scope,
            temporal_scope_filter=request.temporal_scope,
            claims=list(selected.values()),
            relations=list(selected_relations.values()),
            paths=paths,
            evidence=evidence,
            contradiction_candidates=contradictions,
            limitations=limitations,
            actor=actor,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO reasoning_runs(id, created_at, payload) VALUES (?, ?, ?)",
                (result.id, result.created_at.isoformat(), result.model_dump_json()),
            )
        return result

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
