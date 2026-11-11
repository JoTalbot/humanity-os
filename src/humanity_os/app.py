"""HTTP API for the local HUMANITY ONE prototype."""
import hmac
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from humanity_os import __version__
from humanity_os.models import KnowledgeCreate, KnowledgeList, KnowledgeRecord
from humanity_os.store import KnowledgeStore


def create_app(database_path: str | None = None, api_token: str | None = None) -> FastAPI:
    path = database_path or os.environ.get(
        "HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3")
    )
    token = api_token if api_token is not None else os.environ.get("HUMANITY_OS_API_TOKEN")
    if token is not None and len(token) < 32:
        raise ValueError("HUMANITY_OS_API_TOKEN must contain at least 32 characters")

    store = KnowledgeStore(path)
    description = (
        "Local-only prototype. Bearer-token authentication is enabled."
        if token
        else "Local-only prototype without authentication; never expose beyond loopback."
    )
    app = FastAPI(
        title="HUMANITY OS Personal Core",
        version=__version__,
        description=description,
    )
    app.state.knowledge_store = store
    app.state.authentication_enabled = bool(token)

    @app.middleware("http")
    async def require_api_token(request: Request, call_next):
        if token and request.url.path != "/health":
            authorization = request.headers.get("authorization", "")
            scheme, separator, supplied = authorization.partition(" ")
            if (
                not separator
                or scheme.lower() != "bearer"
                or not hmac.compare_digest(supplied, token)
            ):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Valid bearer token required"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

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
            headers={
                "Content-Disposition": 'attachment; filename="humanity-knowledge-export.json"'
            },
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
