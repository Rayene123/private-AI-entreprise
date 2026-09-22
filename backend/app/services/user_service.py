from typing import Any
from uuid import UUID

from app.core.exceptions import AuthorizationError, ResourceNotFoundError
from app.integrations.supabase.client import get_service_supabase_client
from app.schemas.user import CurrentUserProfileResponse
from app.services.permission_service import AuthorizationService


class UserService:
    def __init__(
        self,
        authorization_service: AuthorizationService,
        supabase_client: Any | None = None,
    ) -> None:
        self._authorization_service = authorization_service
        self._supabase = supabase_client or get_service_supabase_client()

    def get_current_user_profile(self, user_id: UUID) -> CurrentUserProfileResponse:
        self._authorization_service.require_permission(user_id, "profile.read")
        profile = self._get_profile(user_id)
        if not profile.get("is_active", False):
            raise AuthorizationError(
                "Application profile is inactive.",
                code="inactive_profile",
            )

        return CurrentUserProfileResponse(
            user_id=user_id,
            display_name=profile.get("display_name"),
            department=profile.get("department_id"),
            roles=self._authorization_service.get_user_roles(user_id),
            permissions=self._authorization_service.get_user_permissions(user_id),
        )

    def _get_profile(self, user_id: UUID) -> dict[str, Any]:
        response = (
            self._supabase.table("profiles")
            .select("id,display_name,department_id,is_active")
            .eq("id", str(user_id))
            .limit(1)
            .execute()
        )
        data = response.get("data") if isinstance(response, dict) else response.data
        if not data:
            raise ResourceNotFoundError(
                "Application profile was not found.",
                code="profile_not_found",
            )
        profile = data[0]
        if not isinstance(profile, dict):
            raise ResourceNotFoundError(
                "Application profile was not found.",
                code="profile_not_found",
            )
        return profile
