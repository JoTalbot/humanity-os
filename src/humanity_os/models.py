"""Versioned API models for the personal knowledge core."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

Visibility = Literal["private", "shared", "public"]
KnowledgeKind = Literal["claim", "concept", "procedure", "observation", "hypothesis", "question", "dataset", "document"]

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class KnowledgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: KnowledgeKind
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=200_000)
    language: str = Field(default="und", min_length=2, max_length=35)
    visibility: Visibility = "private"
    source_uri: str | None = Field(default=None, max_length=2_048)

class KnowledgeRecord(KnowledgeCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = "0.1"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class KnowledgeList(BaseModel):
    items: list[KnowledgeRecord]
    next_cursor: str | None = None
