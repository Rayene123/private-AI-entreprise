import logging

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.error_handlers import register_error_handlers
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    app = FastAPI(
        title=app_settings.app_name,
        debug=False,
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(documents_router)

    logger.info(
        "application_started",
        extra={"app_env": app_settings.app_env},
    )
    return app


app = create_app()
