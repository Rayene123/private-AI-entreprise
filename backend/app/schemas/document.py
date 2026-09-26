from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["active", "archived"]
DocumentAccessLevel = Literal["private", "department", "organization"]


class DocumentCreate(BaseModel):
    title: str
    description: str | None = None
    department_id: UUID | None = None
    access_level: DocumentAccessLevel = "department"
    original_filename: str | None = None
    storage_path: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    department_id: UUID | None = None
    access_level: DocumentAccessLevel | None = None
    original_filename: str | None = None
    storage_path: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    status: DocumentStatus | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentResponse(BaseModel):
    id: UUID
    owner_id: UUID
    department_id: UUID | None = None
    title: str
    description: str | None = None
    original_filename: str | None = None
    storage_path: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    status: DocumentStatus
    access_level: DocumentAccessLevel
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class DocumentFile:
    """An authorized, retrieved document file. Internal use only."""

    content: bytes
    mime_type: str
    filename: str


class DocumentListItem(BaseModel):
    id: UUID
    owner_id: UUID
    department_id: UUID | None = None
    title: str
    description: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    status: DocumentStatus
    access_level: DocumentAccessLevel
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")