from fastapi import APIRouter, Depends

from app.services.health_service import HealthService, get_health_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/dependencies")
async def dependency_health(
    health_service: HealthService = Depends(get_health_service),
) -> dict[str, dict[str, str]]:
    return {"dependencies": health_service.check_dependencies()}
