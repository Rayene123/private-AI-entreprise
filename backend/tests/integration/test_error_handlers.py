from fastapi import Body
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from app.main import create_app


class ExamplePayload(BaseModel):
    name: str
    count: int


def build_client(*, raise_server_exceptions: bool = True) -> TestClient:
    app = create_app()

    @app.get("/test-errors/application")
    async def application_error() -> None:
        raise ValidationError("Input failed validation.")

    @app.get("/test-errors/not-found")
    async def not_found_error() -> None:
        raise ResourceNotFoundError()

    @app.get("/test-errors/authentication")
    async def authentication_error() -> None:
        raise AuthenticationError()

    @app.get("/test-errors/authorization")
    async def authorization_error() -> None:
        raise AuthorizationError()

    @app.get("/test-errors/custom-code")
    async def custom_code_error() -> None:
        raise AppException("Known failure.", code="known_failure")

    @app.get("/test-errors/unexpected")
    async def unexpected_error() -> None:
        raise RuntimeError("Database path C:\\Users\\rayen\\secret.pdf exploded")

    @app.post("/test-errors/validation")
    async def validation_error(
        payload: ExamplePayload = Body(...),
    ) -> dict[str, str]:
        return {"name": payload.name}

    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def test_known_application_exception_returns_error_envelope() -> None:
    client = build_client()

    response = client.get("/test-errors/application")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "Input failed validation."
    assert response.json()["error"]["request_id"]


def test_resource_not_found_exception_returns_404() -> None:
    client = build_client()

    response = client.get("/test-errors/not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"
    assert response.json()["error"]["message"] == "The requested resource was not found."


def test_authentication_exception_returns_401() -> None:
    client = build_client()

    response = client.get("/test-errors/authentication")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.json()["error"]["message"] == "Authentication is required."


def test_authorization_exception_returns_403() -> None:
    client = build_client()

    response = client.get("/test-errors/authorization")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_error"
    assert (
        response.json()["error"]["message"]
        == "You do not have permission to perform this action."
    )


def test_unexpected_exception_returns_safe_500_without_internal_details() -> None:
    client = build_client(raise_server_exceptions=False)

    response = client.get("/test-errors/unexpected")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["message"] == "An internal server error occurred."
    assert "secret.pdf" not in response.text
    assert "RuntimeError" not in response.text


def test_malformed_request_returns_consistent_validation_error() -> None:
    client = build_client()

    response = client.post(
        "/test-errors/validation",
        json={"name": "example", "count": "not-an-integer"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
    assert (
        response.json()["error"]["message"]
        == "The request body or parameters are invalid."
    )


def test_request_id_is_generated_and_returned_in_error_response() -> None:
    client = build_client()

    response = client.get("/test-errors/custom-code")

    request_id = response.json()["error"]["request_id"]
    assert request_id
    assert response.headers["X-Request-ID"] == request_id


def test_incoming_request_id_is_preserved() -> None:
    client = build_client()

    response = client.get(
        "/test-errors/custom-code",
        headers={"X-Request-ID": "request-123"},
    )

    assert response.json()["error"]["request_id"] == "request-123"
    assert response.headers["X-Request-ID"] == "request-123"
