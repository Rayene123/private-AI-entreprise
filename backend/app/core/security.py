from typing import Annotated

from fastapi import Depends, Header

from app.core.exceptions import AuthenticationError
from app.schemas.auth import AuthenticatedUser
from app.services.auth_service import (
    AuthenticationService,
    get_authentication_service,
)


def extract_bearer_token(authorization: str | None) -> str:
    if authorization is None or not authorization.strip():
        raise AuthenticationError(
            "Authentication is required.",
            code="authentication_required",
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AuthenticationError(
            "Invalid authentication header.",
            code="invalid_authentication_header",
        )

    return parts[1]


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    authentication_service: AuthenticationService = Depends(
        get_authentication_service
    ),
) -> AuthenticatedUser:
    token = extract_bearer_token(authorization)
    return authentication_service.authenticate_access_token(token)
