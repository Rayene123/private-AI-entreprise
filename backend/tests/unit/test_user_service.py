from uuid import UUID

import pytest

from app.core.exceptions import ResourceNotFoundError
from app.services.user_service import UserService

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeAuthorizationService:
    def require_permission(self, user_id: UUID, permission_name: str) -> None:
        return None

    def get_user_roles(self, user_id: UUID) -> list[str]:
        return ["employee"]

    def get_user_permissions(self, user_id: UUID) -> list[str]:
        return ["profile.read", "documents.read", "chat.use"]


class FakeQuery:
    def __init__(self, data: list[dict]) -> None:
        self.data = data

    def select(self, columns: str) -> "FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        return self

    def limit(self, count: int) -> "FakeQuery":
        return self

    def execute(self) -> dict[str, list[dict]]:
        return {"data": self.data}


class FakeSupabase:
    def __init__(self, profiles: list[dict]) -> None:
        self.profiles = profiles

    def table(self, table_name: str) -> FakeQuery:
        assert table_name == "profiles"
        return FakeQuery(self.profiles)


def test_current_user_profile_uses_authenticated_user_id() -> None:
    service = UserService(
        FakeAuthorizationService(),
        FakeSupabase(
            [
                {
                    "id": str(USER_ID),
                    "display_name": "Employee User",
                    "department_id": None,
                    "is_active": True,
                }
            ]
        ),
    )

    profile = service.get_current_user_profile(USER_ID)

    assert profile.user_id == USER_ID
    assert profile.roles == ["employee"]


def test_missing_profile_is_handled_safely() -> None:
    service = UserService(FakeAuthorizationService(), FakeSupabase([]))

    with pytest.raises(ResourceNotFoundError) as exc_info:
        service.get_current_user_profile(USER_ID)

    assert exc_info.value.code == "profile_not_found"
