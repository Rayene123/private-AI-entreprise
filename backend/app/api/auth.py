from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.auth import AuthenticatedUser, AuthenticationStatusResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_authenticated_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticationStatusResponse:
    return AuthenticationStatusResponse(
        authenticated=True,
        user_id=current_user.id,
    )
