from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Profile(BaseModel):
    id: UUID
    display_name: str | None = None
    department_id: UUID | None = None
    is_active: bool

    model_config = ConfigDict(extra="forbid")


class Role(BaseModel):
    name: str

    model_config = ConfigDict(extra="forbid")


class Permission(BaseModel):
    name: str

    model_config = ConfigDict(extra="forbid")


class CurrentUserProfileResponse(BaseModel):
    user_id: UUID
    display_name: str | None = None
    department: UUID | None = None
    roles: list[str]
    permissions: list[str]

    model_config = ConfigDict(extra="forbid")
