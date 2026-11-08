from uuid import UUID

from fastapi.testclient import TestClient

from app.api.chat import get_chat_retrieval_service
from app.core.exceptions import AuthorizationError
from app.main import create_app
from app.schemas.auth import AuthenticatedUser
from app.schemas.retrieval import RetrievalResponse
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


class Retrieval:
    def __init__(self, error=None) -> None:
        self.error = error

    def retrieve(self, user_id, query, top_k):
        if self.error:
            raise self.error
        return RetrievalResponse(query=query, results=[], retrieved_count=0)


def client(service: Retrieval | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_authentication_service] = lambda: Auth()
    if service is not None:
        app.dependency_overrides[get_chat_retrieval_service] = lambda: service
    return TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_retrieve_requires_authentication() -> None:
    response = TestClient(create_app()).post(
        "/chat/retrieve",
        json={"query": "leave policy"},
    )
    assert response.status_code == 401


def test_retrieve_returns_structured_empty_result() -> None:
    response = client(Retrieval()).post(
        "/chat/retrieve",
        json={"query": "leave policy", "top_k": 3},
    )
    assert response.status_code == 200
    assert response.json() == {
        "query": "leave policy",
        "results": [],
        "retrieved_count": 0,
    }


def test_retrieve_rejects_empty_query() -> None:
    response = client(Retrieval()).post(
        "/chat/retrieve",
        json={"query": "   "},
    )
    assert response.status_code == 422


def test_retrieve_preserves_safe_permission_error() -> None:
    response = client(
        Retrieval(AuthorizationError(code="insufficient_permissions"))
    ).post(
        "/chat/retrieve",
        json={"query": "leave policy"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"
