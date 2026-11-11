"""HTTP API for the local HUMANITY ONE prototype."""
import hmac
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from humanity_os import __version__
from humanity_os.auth import AuthStore
from humanity_os.models import KnowledgeCreate, KnowledgeList, KnowledgeRecord
from humanity_os.store import KnowledgeStore

SESSION_COOKIE = "humanity_session"
SESSION_MAX_AGE = 12 * 60 * 60


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


def create_app(database_path: str | None = None, api_token: str | None = None) -> FastAPI:
    path = database_path or os.environ.get(
        "HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3")
    )
    token = api_token if api_token is not None else os.environ.get("HUMANITY_OS_API_TOKEN")
    if token is not None and len(token) < 32:
        raise ValueError("HUMANITY_OS_API_TOKEN must contain at least 32 characters")

    store = KnowledgeStore(path)
    auth = AuthStore(path)
    app = FastAPI(
        title="HUMANITY OS Personal Core",
        version=__version__,
        description="Local-only personal workspace with optional owner sessions and bearer auth.",
    )
    app.state.knowledge_store = store
    app.state.auth_store = auth
    app.state.authentication_enabled = bool(token) or auth.has_owner()

    @app.middleware("http")
    async def require_authentication(request: Request, call_next):
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
        required = bool(token) or auth.has_owner()

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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/auth/login")
    def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
        if not auth.has_owner():
            raise HTTPException(status_code=503, detail="Owner password has not been configured")
        if not auth.verify_owner_password(payload.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
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

    @app.post("/auth/logout", status_code=204)
    def logout(request: Request, response: Response) -> Response:
        session_token = request.cookies.get(SESSION_COOKIE)
        if session_token:
            auth.revoke_session(session_token)
        response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
        return Response(status_code=204)

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
        result = store.update(updated)
        if result is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return result

    @app.delete("/v1/knowledge/{record_id}", status_code=204)
    def delete_knowledge(record_id: str) -> Response:
        if not store.delete(record_id):
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return Response(status_code=204)

    return app


app = create_app()
