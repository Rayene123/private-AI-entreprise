from fastapi.testclient import TestClient

from app.api.health import get_health_service
from app.main import create_app


class HealthyDependencyService:
    def check_dependencies(self) -> dict[str, str]:
        return {"supabase": "ok"}


class FailingDependencyService:
    def check_dependencies(self) -> dict[str, str]:
        from app.core.exceptions import IntegrationUnavailableError

        raise IntegrationUnavailableError("Supabase connectivity check failed.")


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dependency_health_returns_supabase_status() -> None:
    app = create_app()
    app.dependency_overrides[get_health_service] = lambda: HealthyDependencyService()
    client = TestClient(app)

    response = client.get("/health/dependencies")

    assert response.status_code == 200
    assert response.json() == {"dependencies": {"supabase": "ok"}}


def test_dependency_health_failure_uses_error_handler() -> None:
    app = create_app()
    app.dependency_overrides[get_health_service] = lambda: FailingDependencyService()
    client = TestClient(app)

    response = client.get(
        "/health/dependencies",
        headers={"X-Request-ID": "dependency-test"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "integration_unavailable",
            "message": "Supabase connectivity check failed.",
            "request_id": "dependency-test",
        }
    }
