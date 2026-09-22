from fastapi import APIRouter, Depends

from app.core.security import require_permission
from app.schemas.auth import AuthenticatedUser
from app.schemas.user import CurrentUserProfileResponse
from app.services.permission_service import (
    AuthorizationService,
    get_authorization_service,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(
    authorization_service: AuthorizationService = Depends(get_authorization_service),
) -> UserService:
    return UserService(authorization_service)


@router.get("/me")
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(require_permission("profile.read")),
    user_service: UserService = Depends(get_user_service),
) -> CurrentUserProfileResponse:
    return user_service.get_current_user_profile(current_user.id)
