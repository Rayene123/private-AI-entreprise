from typing import Any
from uuid import UUID

from app.core.exceptions import AuthorizationError
from app.integrations.supabase.client import get_service_supabase_client


class AuthorizationService:
    def __init__(self, supabase_client: Any | None = None) -> None:
        self._supabase = supabase_client or get_service_supabase_client()

    def get_user_roles(self, user_id: UUID) -> list[str]:
        rows = self._execute(
            self._supabase.table("user_roles")
            .select("roles(id,name)")
            .eq("user_id", str(user_id))
        )
        return sorted(
            {
                role["name"]
                for row in rows
                if isinstance((role := row.get("roles")), dict)
                and isinstance(role.get("name"), str)
            }
        )

    def get_user_permissions(self, user_id: UUID) -> list[str]:
        role_ids = self._get_user_role_ids(user_id)
        if not role_ids:
            return []

        rows = self._execute(
            self._supabase.table("role_permissions")
            .select("permissions(name)")
            .in_("role_id", role_ids)
        )
        return sorted(
            {
                permission["name"]
                for row in rows
                if isinstance((permission := row.get("permissions")), dict)
                and isinstance(permission.get("name"), str)
            }
        )

    def has_role(self, user_id: UUID, role_name: str) -> bool:
        return role_name in self.get_user_roles(user_id)

    def has_permission(self, user_id: UUID, permission_name: str) -> bool:
        return permission_name in self.get_user_permissions(user_id)

    def require_permission(self, user_id: UUID, permission_name: str) -> None:
        if not self.has_permission(user_id, permission_name):
            raise AuthorizationError(
                "You do not have permission to perform this action.",
                code="insufficient_permissions",
            )

    def _get_user_role_ids(self, user_id: UUID) -> list[str]:
        rows = self._execute(
            self._supabase.table("user_roles")
            .select("roles(id,name)")
            .eq("user_id", str(user_id))
        )
        return [
            str(role["id"])
            for row in rows
            if isinstance((role := row.get("roles")), dict)
            and role.get("id") is not None
        ]

    def _execute(self, query: Any) -> list[dict[str, Any]]:
        response = query.execute()
        data = response.get("data") if isinstance(response, dict) else response.data
        if data is None:
            return []
        if not isinstance(data, list):
            return []
        return [row for row in data if isinstance(row, dict)]


def get_authorization_service() -> AuthorizationService:
    return AuthorizationService()
