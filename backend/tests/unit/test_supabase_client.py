import logging
from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import (
    IntegrationConfigurationError,
    IntegrationUnavailableError,
)
from app.core.logging import SensitiveDataFilter
from app.integrations.supabase.client import SupabaseClientFactory


class FakeSupabaseClient:
    def __init__(self, *, should_fail_connectivity: bool = False) -> None:
        self.should_fail_connectivity = should_fail_connectivity

    def table(self, table_name: str) -> "FakeSupabaseClient":
        self.table_name = table_name
        return self

    def select(self, columns: str) -> "FakeSupabaseClient":
        self.columns = columns
        return self

    def limit(self, count: int) -> "FakeSupabaseClient":
        self.count = count
        return self

    def execute(self) -> dict[str, list[Any]]:
        if self.should_fail_connectivity:
            raise RuntimeError("provider-specific failure with credentials")
        return {"data": []}


def build_settings(
    *,
    supabase_url: str | None = "https://example.supabase.co",
    supabase_publishable_key: str | None = "publishable-placeholder",
    supabase_secret_key: str | None = "secret-placeholder",
) -> Settings:
    return Settings(
        supabase_url=supabase_url,
        supabase_publishable_key=(
            SecretStr(supabase_publishable_key)
            if supabase_publishable_key is not None
            else None
        ),
        supabase_secret_key=(
            SecretStr(supabase_secret_key)
            if supabase_secret_key is not None
            else None
        ),
        _env_file=None,
    )


def test_supabase_configuration_loads_from_settings() -> None:
    settings = build_settings()

    assert settings.supabase_url == "https://example.supabase.co"
    assert settings.supabase_publishable_key is not None
    assert (
        settings.supabase_publishable_key.get_secret_value()
        == "publishable-placeholder"
    )
    assert settings.supabase_secret_key is not None
    assert (
        settings.supabase_secret_key.get_secret_value()
        == "secret-placeholder"
    )


def test_missing_supabase_configuration_fails_closed() -> None:
    factory = SupabaseClientFactory(
        build_settings(supabase_url=None),
        create_client_func=lambda url, key: FakeSupabaseClient(),
    )

    with pytest.raises(IntegrationConfigurationError):
        factory.create_user_client()


def test_user_client_uses_publishable_key() -> None:
    calls: list[tuple[str, str]] = []

    def fake_create_client(url: str, key: str) -> FakeSupabaseClient:
        calls.append((url, key))
        return FakeSupabaseClient()

    factory = SupabaseClientFactory(
        build_settings(),
        create_client_func=fake_create_client,
    )

    client = factory.create_user_client()

    assert isinstance(client, FakeSupabaseClient)
    assert calls == [("https://example.supabase.co", "publishable-placeholder")]


def test_service_client_uses_secret_key() -> None:
    calls: list[tuple[str, str]] = []

    def fake_create_client(url: str, key: str) -> FakeSupabaseClient:
        calls.append((url, key))
        return FakeSupabaseClient()

    factory = SupabaseClientFactory(
        build_settings(),
        create_client_func=fake_create_client,
    )

    client = factory.create_service_client()

    assert isinstance(client, FakeSupabaseClient)
    assert calls == [("https://example.supabase.co", "secret-placeholder")]


def test_supabase_credentials_are_not_logged(caplog) -> None:
    def fake_create_client(url: str, key: str) -> FakeSupabaseClient:
        return FakeSupabaseClient()

    factory = SupabaseClientFactory(
        build_settings(),
        create_client_func=fake_create_client,
    )

    with caplog.at_level(logging.INFO):
        factory.create_service_client()

    assert "secret-placeholder" not in caplog.text
    assert "publishable-placeholder" not in caplog.text
    assert "https://example.supabase.co" not in caplog.text


def test_sensitive_log_filter_redacts_supabase_key_fields() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="credential test",
        args=(),
        exc_info=None,
    )
    record.supabase_publishable_key = "publishable-placeholder"
    record.supabase_secret_key = "secret-placeholder"

    SensitiveDataFilter().filter(record)

    assert record.supabase_publishable_key == "[REDACTED]"
    assert record.supabase_secret_key == "[REDACTED]"


def test_connectivity_failure_is_translated_to_application_error() -> None:
    factory = SupabaseClientFactory(
        build_settings(),
        create_client_func=lambda url, key: FakeSupabaseClient(),
    )

    response = httpx.Response(503, request=httpx.Request("GET", "https://example.test"))

    with patch("app.integrations.supabase.client.httpx.Client") as client_class:
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=None)
        client.get.return_value = response
        client_class.return_value = client

        with pytest.raises(IntegrationUnavailableError):
            factory.check_connectivity()


def test_connectivity_check_uses_supabase_health_endpoint_without_logging_keys() -> None:
    factory = SupabaseClientFactory(
        build_settings(),
        create_client_func=lambda url, key: FakeSupabaseClient(),
    )

    response = httpx.Response(200, request=httpx.Request("GET", "https://example.test"))

    with patch("app.integrations.supabase.client.httpx.Client") as client_class:
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=None)
        client.get.return_value = response
        client_class.return_value = client

        assert factory.check_connectivity() is True

    client.get.assert_called_once()
    url = client.get.call_args.args[0]
    assert url == "https://example.supabase.co/auth/v1/health"
    assert "headers" not in client.get.call_args.kwargs


def test_connectivity_check_requires_configuration() -> None:
    factory = SupabaseClientFactory(
        build_settings(supabase_publishable_key=None),
        create_client_func=lambda url, key: FakeSupabaseClient(),
    )

    with pytest.raises(IntegrationConfigurationError):
        factory.check_connectivity()
