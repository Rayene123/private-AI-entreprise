from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuthenticatedUser(BaseModel):
    id: UUID
    email: str | None = None
    role: str | None = None
    claims: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class AuthenticationStatusResponse(BaseModel):
    authenticated: bool
    user_id: UUID

    model_config = ConfigDict(extra="forbid")
