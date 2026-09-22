from uuid import UUID

from fastapi.testclient import TestClient

from app.core.exceptions import AuthenticationError
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.services.auth_service import get_authentication_service

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class SuccessfulAuthService:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=USER_ID,
            email=None,
            role="authenticated",
            claims={"sub": str(USER_ID), "role": "authenticated"},
        )


class InvalidTokenAuthService:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        raise AuthenticationError(
            "Invalid access token.",
            code="invalid_access_token",
        )


def build_client(auth_service) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_authentication_service] = lambda: auth_service
    return TestClient(app)


def test_health_remains_public_without_authentication() -> None:
    client = build_client(InvalidTokenAuthService())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_authorization_header_returns_401() -> None:
    client = build_client(SuccessfulAuthService())

    response = client.get("/auth/me", headers={"X-Request-ID": "missing-auth"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.json()["error"]["request_id"] == "missing-auth"


def test_malformed_authorization_header_returns_401() -> None:
    client = build_client(SuccessfulAuthService())

    malformed_headers = [
        "Basic abc",
        "Bearer",
        "Bearer ",
        "Bearer token extra",
        "token",
    ]

    for header in malformed_headers:
        response = client.get("/auth/me", headers={"Authorization": header})

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_authentication_header"


def test_invalid_token_returns_401() -> None:
    client = build_client(InvalidTokenAuthService())

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


def test_valid_token_returns_authenticated_user_id() -> None:
    client = build_client(SuccessfulAuthService())

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer verified-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "user_id": str(USER_ID),
    }
