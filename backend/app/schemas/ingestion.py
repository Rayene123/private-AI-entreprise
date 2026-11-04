from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IngestionChunk(BaseModel):
    document_id: UUID
    chunk_index: int
    text: str
    source_hash: str
    page_number: int | None = None
    chunk_id: str

    model_config = ConfigDict(extra="forbid")


class IngestionResponse(BaseModel):
    document_id: UUID
    source_hash: str
    file_type: str
    markdown_length: int
    chunk_count: int
    markdown: str
    chunks: list[IngestionChunk]
    indexed_count: int | None = None
    embedding_model: str | None = None
    indexing_status: str | None = None

    model_config = ConfigDict(extra="forbid")
