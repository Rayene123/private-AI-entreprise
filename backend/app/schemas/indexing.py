from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IndexingResponse(BaseModel):
    document_id: UUID
    source_hash: str
    chunk_count: int
    indexed_count: int
    embedding_model: str
    indexing_status: str

    model_config = ConfigDict(extra="forbid")
