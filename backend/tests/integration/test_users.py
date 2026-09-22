from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.api.users import get_user_service
from app.core.exceptions import AuthenticationError
from app.core.security import require_permission
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.schemas.user import CurrentUserProfileResponse
from app.services.auth_service import get_authentication_service
from app.services.permission_service import get_authorization_service

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class SuccessfulAuthService:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=USER_ID,
            email="employee@example.com",
            role="authenticated",
            claims={"sub": str(USER_ID), "role": "authenticated"},
        )


class InvalidTokenAuthService:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        raise AuthenticationError(
            "Invalid access token.",
            code="invalid_access_token",
        )


class FakeAuthorizationService:
    def __init__(self, permissions: set[str], roles: list[str] | None = None) -> None:
        self.permissions = permissions
        self.roles = roles or ["employee"]

    def has_permission(self, user_id: UUID, permission_name: str) -> bool:
        return permission_name in self.permissions

    def get_user_roles(self, user_id: UUID) -> list[str]:
        return self.roles

    def get_user_permissions(self, user_id: UUID) -> list[str]:
        return sorted(self.permissions)


class FakeUserService:
    def get_current_user_profile(
        self,
        user_id: UUID,
    ) -> CurrentUserProfileResponse:
        return CurrentUserProfileResponse(
            user_id=user_id,
            display_name="Employee User",
            department=None,
            roles=["employee"],
            permissions=[
                "chat.use",
                "documents.read",
                "profile.read",
                "profile.update",
            ],
        )


def build_client(
    *,
    auth_service,
    permissions: set[str],
    roles: list[str] | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_authentication_service] = lambda: auth_service
    app.dependency_overrides[get_authorization_service] = lambda: (
        FakeAuthorizationService(permissions, roles)
    )
    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    return TestClient(app)


def test_authenticated_user_can_retrieve_own_profile() -> None:
    client = build_client(
        auth_service=SuccessfulAuthService(),
        permissions={"profile.read"},
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(USER_ID),
        "display_name": "Employee User",
        "department": None,
        "roles": ["employee"],
        "permissions": [
            "chat.use",
            "documents.read",
            "profile.read",
            "profile.update",
        ],
    }


def test_users_me_without_authentication_returns_401() -> None:
    client = build_client(
        auth_service=SuccessfulAuthService(),
        permissions={"profile.read"},
    )

    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_users_me_with_invalid_token_returns_401() -> None:
    client = build_client(
        auth_service=InvalidTokenAuthService(),
        permissions={"profile.read"},
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


def test_authenticated_user_without_permission_returns_403() -> None:
    client = build_client(
        auth_service=SuccessfulAuthService(),
        permissions=set(),
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


def test_require_permission_dependency_boundary() -> None:
    router = APIRouter()

    @router.get("/permission-test")
    async def permission_test(
        current_user: AuthenticatedUser = Depends(
            require_permission("documents.read")
        ),
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    app = create_app()
    app.include_router(router)
    app.dependency_overrides[get_authentication_service] = lambda: (
        SuccessfulAuthService()
    )
    app.dependency_overrides[get_authorization_service] = lambda: (
        FakeAuthorizationService({"documents.read"})
    )
    client = TestClient(app)

    response = client.get(
        "/permission-test",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": str(USER_ID)}


def test_require_permission_dependency_denies_unauthorized_user() -> None:
    router = APIRouter()

    @router.get("/permission-test")
    async def permission_test(
        current_user: AuthenticatedUser = Depends(
            require_permission("documents.read")
        ),
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    app = create_app()
    app.include_router(router)
    app.dependency_overrides[get_authentication_service] = lambda: (
        SuccessfulAuthService()
    )
    app.dependency_overrides[get_authorization_service] = lambda: (
        FakeAuthorizationService(set())
    )
    client = TestClient(app)

    response = client.get(
        "/permission-test",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


def test_employee_cannot_use_users_manage_dependency() -> None:
    router = APIRouter()

    @router.get("/manage-users-test")
    async def manage_users_test(
        current_user: AuthenticatedUser = Depends(require_permission("users.manage")),
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    app = create_app()
    app.include_router(router)
    app.dependency_overrides[get_authentication_service] = lambda: (
        SuccessfulAuthService()
    )
    app.dependency_overrides[get_authorization_service] = lambda: (
        FakeAuthorizationService({"profile.read", "documents.read", "chat.use"})
    )
    client = TestClient(app)

    response = client.get(
        "/manage-users-test",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


def test_authorized_user_can_use_users_manage_dependency() -> None:
    router = APIRouter()

    @router.get("/manage-users-test")
    async def manage_users_test(
        current_user: AuthenticatedUser = Depends(require_permission("users.manage")),
    ) -> dict[str, str]:
        return {"user_id": str(current_user.id)}

    app = create_app()
    app.include_router(router)
    app.dependency_overrides[get_authentication_service] = lambda: (
        SuccessfulAuthService()
    )
    app.dependency_overrides[get_authorization_service] = lambda: (
        FakeAuthorizationService({"users.manage"}, ["admin"])
    )
    client = TestClient(app)

    response = client.get(
        "/manage-users-test",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": str(USER_ID)}


def test_privilege_mutation_routes_do_not_exist() -> None:
    client = build_client(
        auth_service=SuccessfulAuthService(),
        permissions={"profile.read", "users.manage"},
        roles=["admin"],
    )

    role_response = client.put(
        f"/users/{USER_ID}/role",
        json={"role": "admin"},
        headers={"Authorization": "Bearer verified-token"},
    )
    permission_response = client.put(
        f"/users/{USER_ID}/permissions",
        json={"permissions": ["users.manage"]},
        headers={"Authorization": "Bearer verified-token"},
    )

    assert role_response.status_code == 404
    assert permission_response.status_code == 404


def test_service_role_secret_not_returned_in_users_me_response() -> None:
    client = build_client(
        auth_service=SuccessfulAuthService(),
        permissions={"profile.read"},
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert "SUPABASE_SECRET_KEY" not in response.text
    assert "service_role" not in response.text
