from uuid import UUID

from fastapi.testclient import TestClient

from app.api.chat import get_generation_service
from app.core.exceptions import AuthorizationError
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.schemas.generation import AnswerResponse
from app.services.auth_service import get_authentication_service

USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class Auth:
    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=USER_ID,
            email="employee@example.com",
            role="authenticated",
            claims={"sub": str(USER_ID), "role": "authenticated"},
        )


class Generation:
    def __init__(self, error=None):
        self.error = error

    def ask(self, user_id, query):
        if self.error:
            raise self.error
        return AnswerResponse(
            answer="Grounded answer",
            citations=[],
            has_sufficient_context=True,
        )


def client(service) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_authentication_service] = lambda: Auth()
    app.dependency_overrides[get_generation_service] = lambda: service
    return TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_ask_returns_structured_answer() -> None:
    response = client(Generation()).post(
        "/chat/ask",
        json={"query": "leave policy"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Grounded answer"


def test_ask_preserves_permission_failure() -> None:
    response = client(
        Generation(AuthorizationError(code="insufficient_permissions"))
    ).post(
        "/chat/ask",
        json={"query": "leave policy"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"
