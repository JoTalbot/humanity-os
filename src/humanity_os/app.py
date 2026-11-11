"""HTTP API for the local HUMANITY ONE prototype."""
import os
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, Response
from humanity_os import __version__
from humanity_os.models import KnowledgeCreate, KnowledgeList, KnowledgeRecord
from humanity_os.store import KnowledgeStore

def create_app(database_path: str | None = None) -> FastAPI:
    path = database_path or os.environ.get("HUMANITY_OS_DB", str(Path.home() / ".humanity-os" / "knowledge.sqlite3"))
    store = KnowledgeStore(path)
    app = FastAPI(title="HUMANITY OS Personal Core", version=__version__,
        description="Local-only prototype. No authentication: never expose beyond loopback.")
    app.state.knowledge_store = store

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/knowledge", response_model=KnowledgeRecord, status_code=201)
    def create_knowledge(payload: KnowledgeCreate) -> KnowledgeRecord:
        return store.create(KnowledgeRecord(**payload.model_dump()))

    @app.get("/v1/knowledge", response_model=KnowledgeList)
    def list_knowledge(limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None) -> KnowledgeList:
        try:
            records = store.list(limit=limit, cursor=cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        next_cursor = store.encode_cursor(records[-1]) if len(records) == limit else None
        return KnowledgeList(items=records, next_cursor=next_cursor)

    @app.get("/v1/knowledge/{record_id}", response_model=KnowledgeRecord)
    def get_knowledge(record_id: str) -> KnowledgeRecord:
        record = store.get(record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return record

    @app.delete("/v1/knowledge/{record_id}", status_code=204)
    def delete_knowledge(record_id: str) -> Response:
        if not store.delete(record_id):
            raise HTTPException(status_code=404, detail="Knowledge record not found")
        return Response(status_code=204)

    return app

app = create_app()
