from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Query must not be empty.")
        return normalized

    model_config = ConfigDict(extra="forbid")


class RetrievedChunkMetadata(BaseModel):
    source_filename: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    chunk_index: int | None = None
    source_hash: str | None = None

    model_config = ConfigDict(extra="forbid")


class RetrievedChunk(BaseModel):
    document_id: UUID
    chunk_id: str
    content: str
    score: float
    metadata: RetrievedChunkMetadata

    model_config = ConfigDict(extra="forbid")


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievedChunk]
    retrieved_count: int

    model_config = ConfigDict(extra="forbid")
