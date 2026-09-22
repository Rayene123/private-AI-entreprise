import logging
from enum import StrEnum
from typing import Any, Protocol

import httpx
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    IntegrationConfigurationError,
    IntegrationUnavailableError,
)

logger = logging.getLogger(__name__)


class SupabaseCreateClient(Protocol):
    def __call__(self, supabase_url: str, supabase_key: str) -> Any:
        ...


class SupabaseAccessLevel(StrEnum):
    USER = "user"
    SERVICE = "service"


class SupabaseClientFactory:
    """Creates Supabase clients without leaking credential material."""

    def __init__(
        self,
        settings: Settings,
        *,
        create_client_func: SupabaseCreateClient | None = None,
    ) -> None:
        self._settings = settings
        self._create_client = create_client_func or self._load_create_client()

    def create_user_client(self) -> Any:
        return self._create_client_for(
            access_level=SupabaseAccessLevel.USER,
            key=self._settings.supabase_publishable_key,
        )

    def create_service_client(self) -> Any:
        logger.info(
            "creating_service_supabase_client",
            extra={"supabase_access_level": SupabaseAccessLevel.SERVICE.value},
        )
        return self._create_client_for(
            access_level=SupabaseAccessLevel.SERVICE,
            key=self._settings.supabase_secret_key,
        )

    def check_connectivity(self, *, use_service_role: bool = False) -> bool:
        access_level = self._access_level(use_service_role)
        key = (
            self._settings.supabase_secret_key
            if use_service_role
            else self._settings.supabase_publishable_key
        )
        supabase_url = self._settings.supabase_url
        if not supabase_url or not key:
            logger.error(
                "supabase_configuration_missing",
                extra={"supabase_access_level": access_level},
            )
            raise IntegrationConfigurationError(
                "Supabase integration is not configured."
            )

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{supabase_url.rstrip('/')}/auth/v1/health",
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "supabase_connectivity_check_failed",
                extra={
                    "supabase_access_level": access_level,
                    "status_code": exc.response.status_code,
                },
            )
            raise IntegrationUnavailableError(
                "Supabase connectivity check failed."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "supabase_connectivity_check_failed",
                extra={"supabase_access_level": access_level},
            )
            raise IntegrationUnavailableError(
                "Supabase connectivity check failed."
            ) from exc

        return True

    def _create_client_for(
        self,
        *,
        access_level: SupabaseAccessLevel,
        key: SecretStr | None,
    ) -> Any:
        supabase_url = self._settings.supabase_url
        if not supabase_url or not key:
            logger.error(
                "supabase_configuration_missing",
                extra={"supabase_access_level": access_level.value},
            )
            raise IntegrationConfigurationError(
                "Supabase integration is not configured."
            )

        try:
            return self._create_client(supabase_url, key.get_secret_value())
        except Exception as exc:
            logger.exception(
                "supabase_client_creation_failed",
                extra={"supabase_access_level": access_level.value},
            )
            raise IntegrationUnavailableError(
                "Supabase client could not be created."
            ) from exc

    def _load_create_client(self) -> SupabaseCreateClient:
        try:
            from supabase import create_client
        except ImportError as exc:
            raise IntegrationConfigurationError(
                "Supabase client dependency is not installed."
            ) from exc

        return create_client

    def _access_level(self, use_service_role: bool) -> str:
        if use_service_role:
            return SupabaseAccessLevel.SERVICE.value
        return SupabaseAccessLevel.USER.value


def get_supabase_client(settings: Settings | None = None) -> Any:
    return SupabaseClientFactory(settings or get_settings()).create_user_client()


def get_service_supabase_client(settings: Settings | None = None) -> Any:
    return SupabaseClientFactory(settings or get_settings()).create_service_client()
