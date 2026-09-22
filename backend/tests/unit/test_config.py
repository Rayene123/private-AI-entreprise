from app.core.config import Settings


def test_settings_load_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "Test Enterprise AI")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-placeholder")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret-placeholder")
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("JWT_ISSUER", "https://example.supabase.co/auth/v1")

    settings = Settings()

    assert settings.app_name == "Test Enterprise AI"
    assert settings.app_env == "test"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
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
    assert settings.jwt_audience == "authenticated"
    assert settings.jwt_issuer == "https://example.supabase.co/auth/v1"


def test_invalid_debug_value_defaults_to_false(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "release")

    settings = Settings()

    assert settings.debug is False

