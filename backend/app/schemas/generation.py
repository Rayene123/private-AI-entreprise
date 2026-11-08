from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Query must not be empty.")
        return value

    model_config = ConfigDict(extra="forbid")


class AnswerCitation(BaseModel):
    document_id: UUID
    chunk_id: str
    filename: str | None = None
    page_number: int | None = None
    chunk_index: int | None = None

    model_config = ConfigDict(extra="forbid")


class AnswerResponse(BaseModel):
    answer: str
    citations: list[AnswerCitation]
    has_sufficient_context: bool

    model_config = ConfigDict(extra="forbid")
