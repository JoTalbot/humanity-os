"""HTTP API for the local HUMANITY ONE prototype."""
import hashlib
import hmac
import ipaddress
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from humanity_os import __version__
from humanity_os.auth import AuthStore
from humanity_os.claim_assessments import ClaimAssessmentStore
from humanity_os.claim_graph import ClaimGraphStore
from humanity_os.documents import MAX_DOCUMENT_CHARS, DocumentStore
from humanity_os.evidence import EvidenceAssessmentStore
from humanity_os.independence import (
    EvidenceIndependenceEngine,
    EvidenceIndependenceReport,
    IndependenceQuery,
)
from humanity_os.model_gateway import (
    ModelGateway,
    ModelGenerationRequest,
    ModelGenerationResponse,
    ModelProvider,
    ModelProviderFailure,
    ModelProviderTimeout,
    ModelProviderUnavailable,
)
from humanity_os.models import (
    ClaimAssessment,
    ClaimAssessmentCreate,
    ClaimCreate,
    ClaimNode,
    ClaimRelation,
    ClaimRelationCreate,
    ConflictCreate,
    ConflictDecision,
    DecisionCreate,
    DecisionRecord,
    EvidenceAssessment,
    EvidenceAssessmentCreate,
    KnowledgeConflict,
    KnowledgeCreate,
    KnowledgeList,
    KnowledgeRecord,
    KnowledgeRevision,
)
from humanity_os.reasoning import (
    ReasoningComparison,
    ReasoningComparisonQuery,
    ReasoningEngine,
    ReasoningQuery,
    ReasoningRun,
)
from humanity_os.store import KnowledgeStore

SESSION_COOKIE = "humanity_session"
SESSION_MAX_AGE = 12 * 60 * 60


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=MAX_DOCUMENT_CHARS)


class DocumentSearch(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    limit: int = Field(default=20, ge=1, le=50)


def create_app(
    database_path: str | None = None,
    api_token: str | None = None,
    *,
    allow_unauthenticated_local: bool = False,
    model_provider: ModelProvider | None = None,
) -> FastAPI:
    path = database_path or os.environ.get(
        "HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3")
    )
    token = api_token if api_token is not None else os.environ.get("HUMANITY_OS_API_TOKEN")
    if token is not None and len(token) < 32:
        raise ValueError("HUMANITY_OS_API_TOKEN must contain at least 32 characters")

    store = KnowledgeStore(path)
    documents = DocumentStore(path)
    auth = AuthStore(path)
    evidence_assessments = EvidenceAssessmentStore(store.database_path)
    claim_graph = ClaimGraphStore(store.database_path)
    claim_assessments = ClaimAssessmentStore(store.database_path)
    reasoning = ReasoningEngine(store.database_path, store, claim_graph)
    independence = EvidenceIndependenceEngine(store)
    model_gateway = ModelGateway(model_provider)
    app = FastAPI(
        title="HUMANITY OS Personal Core",
        version=__version__,
        description="Loopback-only personal workspace with mandatory authentication by default.",
    )
    app.state.knowledge_store = store
    app.state.document_store = documents
    app.state.auth_store = auth
    app.state.evidence_assessment_store = evidence_assessments
    app.state.claim_graph_store = claim_graph
    app.state.claim_assessment_store = claim_assessments
    app.state.reasoning_engine = reasoning
    app.state.evidence_independence_engine = independence
    app.state.model_gateway = model_gateway
    app.state.authentication_enabled = not allow_unauthenticated_local or bool(token) or auth.has_owner()

    @app.middleware("http")
    async def require_authentication(request: Request, call_next):
        # Enforce the network boundary inside the ASGI application as well as in
        # the CLI. Direct Uvicorn/ASGI startup must not bypass loopback-only mode.
        peer_host = request.client.host if request.client else ""
        try:
            peer_is_loopback = ipaddress.ip_address(peer_host).is_loopback
        except ValueError:
            peer_is_loopback = peer_host.lower() == "localhost"
        if not peer_is_loopback:
            return JSONResponse(status_code=403, content={"detail": "Loopback clients only"})

        if request.url.path in {"/health", "/auth/login"}:
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        bearer_valid = bool(
            token
            and separator
            and scheme.lower() == "bearer"
            and hmac.compare_digest(supplied, token)
        )
        session_token = request.cookies.get(SESSION_COOKIE)
        session_valid = bool(session_token and auth.validate_session(session_token))
        required = not allow_unauthenticated_local or bool(token) or auth.has_owner()

        if required and not (bearer_valid or session_valid):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if session_valid and not bearer_valid and request.method not in {"GET", "HEAD", "OPTIONS"}:
            csrf = request.headers.get("x-csrf-token", "")
            if not csrf or not auth.validate_csrf(session_token, csrf):
                return JSONResponse(
                    status_code=403, content={"detail": "Valid X-CSRF-Token header required"}
                )
        request.state.auth_session_token = session_token if session_valid else None
        return await call_next(request)

    @app.post("/v1/models/generate", response_model=ModelGenerationResponse)
    async def generate_model_output(
        payload: ModelGenerationRequest,
    ) -> ModelGenerationResponse:
        try:
            return await model_gateway.generate(payload)
        except ModelProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail="No model provider is configured") from exc
        except ModelProviderTimeout as exc:
            raise HTTPException(status_code=504, detail="Model provider timed out") from exc
        except ModelProviderFailure as exc:
            raise HTTPException(status_code=502, detail="Model provider request failed") from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/auth/login")
    def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
        if not auth.has_owner():
            raise HTTPException(status_code=503, detail="Owner password has not been configured")

        remote_host = request.client.host if request.client else "unknown"
        ip_bucket = "ip:" + hashlib.sha256(remote_host.encode("utf-8")).hexdigest()
        buckets = ("owner", ip_bucket)
        retry_after = auth.consume_login_attempts(buckets)
        if retry_after:
            auth.record_audit_event("login_rate_limited", "owner")
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts; try again later",
                headers={"Retry-After": str(retry_after)},
            )

        if not auth.verify_owner_password(payload.password):
            auth.record_audit_event("login_failed", ip_bucket)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        for bucket in buckets:
            auth.clear_login_failures(bucket)
        auth.record_audit_event("login_succeeded", "owner")
        session_token, csrf_token = auth.create_session()
        response.set_cookie(
            SESSION_COOKIE,
            session_token,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            path="/",
        )
        return {"authenticated": "true", "csrf_token": csrf_token}

    @app.get("/auth/events")
    def auth_events(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        before_id: Annotated[int | None, Query(ge=1)] = None,
    ) -> dict[str, list[dict]]:
        return {"items": auth.list_audit_events(limit=limit, before_id=before_id)}

    @app.post("/auth/logout", status_code=204)
    def logout(request: Request, response: Response) -> Response:
        session_token = request.cookies.get(SESSION_COOKIE)
        if session_token:
            auth.revoke_session(session_token)
        response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
        response.status_code = 204
        return response

    @app.post("/v1/decisions", response_model=DecisionRecord, status_code=201)
    def create_decision(payload: DecisionCreate, request: Request) -> DecisionRecord:
        for record_id in payload.related_knowledge_ids:
            if store.get(record_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Related knowledge record not found: {record_id}",
                )
        actor = "owner" if request.state.auth_session_token else "system"
        decision = DecisionRecord(**payload.model_dump(), actor=actor)
        return store.create_decision(decision)

    @app.get("/v1/decisions", response_model=list[DecisionRecord])
    def list_decisions(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[DecisionRecord]:
        return store.list_decisions(limit=limit)

    @app.get("/v1/decisions/{decision_id}", response_model=DecisionRecord)
    def get_decision(decision_id: str) -> DecisionRecord:
        decision = store.get_decision(decision_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        return decision

    @app.post("/v1/conflicts", response_model=KnowledgeConflict, status_code=201)
    def create_conflict(payload: ConflictCreate) -> KnowledgeConflict:
        if store.get(payload.record_a_id) is None or store.get(payload.record_b_id) is None:
            raise HTTPException(status_code=404, detail="Both knowledge records must exist")
        record_a_id, record_b_id = sorted((payload.record_a_id, payload.record_b_id))
        conflict = KnowledgeConflict(
            record_a_id=record_a_id,
            record_b_id=record_b_id,
            reason=payload.reason,
        )
        try:
            return store.create_conflict(conflict)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409, detail="A conflict for this record pair already exists"
            ) from exc

    @app.get("/v1/conflicts")
    def list_conflicts(
        status: Annotated[
            str | None,
            Query(pattern="^(pending_review|resolved|dismissed)$"),
        ] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> dict[str, list[KnowledgeConflict]]:
        return {"items": store.list_conflicts(status=status, limit=limit)}

    @app.post(
        "/v1/conflicts/{conflict_id}/decision",
        response_model=KnowledgeConflict,
    )
    def decide_conflict(
        conflict_id: str, payload: ConflictDecision
    ) -> KnowledgeConflict:
        decided = store.decide_conflict(
            conflict_id, payload.status, payload.resolution_note
        )
        if decided is None:
            existing = store.get_conflict(conflict_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="Conflict not found")
            raise HTTPException(status_code=409, detail="Conflict is no longer pending review")
        return decided

    @app.post("/v1/claims", response_model=ClaimNode, status_code=201)
    def create_claim(payload: ClaimCreate, request: Request) -> ClaimNode:
        record = store.get(payload.knowledge_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        if record.kind != "claim":
            raise HTTPException(status_code=422, detail="Claims must be grounded in a claim knowledge record")
        declared_evidence_ids = {item.id for item in record.evidence}
        if set(payload.evidence_ids) - declared_evidence_ids:
            raise HTTPException(status_code=422, detail="Claim evidence IDs must exist on the linked knowledge record")
        claim = ClaimNode(
            **payload.model_dump(),
            actor="owner" if request.state.auth_session_token else "system",
        )
        return claim_graph.create_claim(claim)

    @app.get("/v1/claims", response_model=list[ClaimNode])
    def list_claims(
        knowledge_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[ClaimNode]:
        if knowledge_id is not None and store.get(knowledge_id) is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return claim_graph.list_claims(knowledge_id=knowledge_id, limit=limit)

    @app.get("/v1/claims/{claim_id}", response_model=ClaimNode)
    def get_claim(claim_id: str) -> ClaimNode:
        claim = claim_graph.get_claim(claim_id)
        if claim is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim

    @app.post(
        "/v1/claims/{claim_id}/assessments",
        response_model=ClaimAssessment,
        status_code=201,
    )
    def create_claim_assessment(
        claim_id: str, payload: ClaimAssessmentCreate, request: Request
    ) -> ClaimAssessment:
        if claim_graph.get_claim(claim_id) is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        assessment = ClaimAssessment(
            **payload.model_dump(),
            claim_id=claim_id,
            actor="owner" if request.state.auth_session_token else "system",
        )
        return claim_assessments.create(assessment)

    @app.get(
        "/v1/claims/{claim_id}/assessments",
        response_model=list[ClaimAssessment],
    )
    def list_claim_assessments(
        claim_id: str,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[ClaimAssessment]:
        if claim_graph.get_claim(claim_id) is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim_assessments.list_for_claim(claim_id, limit=limit)

    @app.post("/v1/claim-relations", response_model=ClaimRelation, status_code=201)
    def create_claim_relation(
        payload: ClaimRelationCreate, request: Request
    ) -> ClaimRelation:
        if claim_graph.get_claim(payload.source_claim_id) is None:
            raise HTTPException(status_code=404, detail="Source claim not found")
        if claim_graph.get_claim(payload.target_claim_id) is None:
            raise HTTPException(status_code=404, detail="Target claim not found")
        relation = ClaimRelation(
            **payload.model_dump(),
            actor="owner" if request.state.auth_session_token else "system",
        )
        try:
            return claim_graph.create_relation(relation)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409, detail="This claim relation already exists"
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/claim-relations", response_model=list[ClaimRelation])
    def list_claim_relations(
        claim_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[ClaimRelation]:
        if claim_id is not None and claim_graph.get_claim(claim_id) is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        return claim_graph.list_relations(claim_id=claim_id, limit=limit)

    @app.post("/v1/reasoning/runs", response_model=ReasoningRun, status_code=201)
    def create_reasoning_run(payload: ReasoningQuery, request: Request) -> ReasoningRun:
        actor = "owner" if request.state.auth_session_token else "system"
        try:
            return reasoning.run(payload, actor=actor)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/v1/reasoning/compare",
        response_model=ReasoningComparison,
        status_code=201,
    )
    def compare_reasoning_paths(
        payload: ReasoningComparisonQuery, request: Request
    ) -> ReasoningComparison:
        actor = "owner" if request.state.auth_session_token else "system"
        try:
            return reasoning.compare(payload, actor=actor)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/reasoning/runs/{run_id}", response_model=ReasoningRun)
    def get_reasoning_run(run_id: str) -> ReasoningRun:
        result = reasoning.get(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Reasoning run not found")
        return result

    @app.post(
        "/v1/evidence-independence/analyze",
        response_model=EvidenceIndependenceReport,
    )
    def analyze_evidence_independence(
        payload: IndependenceQuery,
    ) -> EvidenceIndependenceReport:
        try:
            return independence.analyze(payload)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/v1/evidence-assessments",
        response_model=EvidenceAssessment,
        status_code=201,
    )
    def create_evidence_assessment(
        payload: EvidenceAssessmentCreate, request: Request
    ) -> EvidenceAssessment:
        record = store.get(payload.knowledge_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        source_ids = {source.id for source in record.sources}
        if payload.source_id not in source_ids:
            raise HTTPException(status_code=404, detail="Source is not declared on this knowledge record")
        if payload.evidence_id is not None:
            matching_evidence = next(
                (item for item in record.evidence if item.id == payload.evidence_id),
                None,
            )
            if matching_evidence is None or matching_evidence.source_id != payload.source_id:
                raise HTTPException(
                    status_code=422,
                    detail="Evidence ID must identify evidence linked to the declared source",
                )
        assessment = EvidenceAssessment(
            **payload.model_dump(),
            actor="owner" if request.state.auth_session_token else "system",
        )
        return evidence_assessments.create(assessment)

    @app.get("/v1/evidence-assessments", response_model=list[EvidenceAssessment])
    def list_evidence_assessments(
        knowledge_id: Annotated[str, Query(min_length=1, max_length=128)],
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[EvidenceAssessment]:
        if store.get(knowledge_id) is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return evidence_assessments.list_for_knowledge(knowledge_id, limit=limit)

    @app.post("/v1/documents", status_code=201)
    def create_document(payload: DocumentCreate) -> dict:
        try:
            return documents.create(payload.filename, payload.content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/documents")
    def list_documents(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> dict[str, list[dict]]:
        return {"items": documents.list(limit=limit)}

    @app.get("/v1/documents/{document_id}")
    def get_document(document_id: str) -> dict:
        result = documents.get(document_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return result

    @app.post("/v1/documents/search")
    def search_documents(payload: DocumentSearch) -> dict[str, list[dict]]:
        try:
            return {"items": documents.search(payload.query, limit=payload.limit)}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/v1/knowledge", response_model=KnowledgeRecord, status_code=201)
    def create_knowledge(payload: KnowledgeCreate) -> KnowledgeRecord:
        return store.create(KnowledgeRecord(**payload.model_dump()))

    @app.get("/v1/knowledge", response_model=KnowledgeList)
    def list_knowledge(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    ) -> KnowledgeList:
        try:
            records = store.list(limit=limit, cursor=cursor, query=q)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        next_cursor = store.encode_cursor(records[-1]) if len(records) == limit else None
        return KnowledgeList(items=records, next_cursor=next_cursor)

    @app.get("/v1/workspace/export")
    def export_workspace() -> JSONResponse:
        document = store.export_workspace()
        return JSONResponse(
            content=document,
            headers={
                "Content-Disposition": 'attachment; filename="humanity-os-workspace.json"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/v1/knowledge/export")
    def export_knowledge() -> JSONResponse:
        records = store.export_all()
        return JSONResponse(
            content={
                "schema_version": "0.1",
                "exported_at": datetime.now(UTC).isoformat(),
                "items": [record.model_dump(mode="json") for record in records],
            },
            headers={"Content-Disposition": 'attachment; filename="humanity-knowledge-export.json"'},
        )

    @app.get("/v1/knowledge/{record_id}", response_model=KnowledgeRecord)
    def get_knowledge(record_id: str) -> KnowledgeRecord:
        record = store.get(record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return record

    @app.put("/v1/knowledge/{record_id}", response_model=KnowledgeRecord)
    def update_knowledge(record_id: str, payload: KnowledgeCreate) -> KnowledgeRecord:
        existing = store.get(record_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        updated = existing.model_copy(
            update={**payload.model_dump(), "updated_at": datetime.now(UTC)}
        )
        result = store.update(updated, actor="owner" if auth.has_owner() else "system")
        if result is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return result

    @app.get(
        "/v1/knowledge/{record_id}/revisions",
        response_model=list[KnowledgeRevision],
    )
    def list_knowledge_revisions(
        record_id: str,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> list[KnowledgeRevision]:
        revisions = store.list_revisions(record_id, limit=limit)
        if not revisions:
            raise HTTPException(status_code=404, detail="Knowledge record or revision history not found")
        return revisions

    @app.delete("/v1/knowledge/{record_id}", status_code=204)
    def delete_knowledge(record_id: str) -> Response:
        try:
            deleted = store.delete(record_id)
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=409,
                detail="Knowledge record is linked to a conflict; review or remove the conflict first",
            ) from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return Response(status_code=204)

    return app


app = create_app()
