import logging
from uuid import UUID

import pytest
from supabase_auth.errors import AuthInvalidJwtError

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.services.auth_service import AuthenticationService

USER_ID = "11111111-1111-1111-1111-111111111111"
JWT_ISSUER = "https://example.supabase.co/auth/v1"
JWT_AUDIENCE = "authenticated"


def build_settings() -> Settings:
    return Settings(
        jwt_issuer=JWT_ISSUER,
        jwt_audience=JWT_AUDIENCE,
        _env_file=None,
    )


def valid_claims() -> dict[str, object]:
    return {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": USER_ID,
        "email": "user@example.com",
        "role": "authenticated",
        "exp": 4_102_444_800,
        "iat": 1_700_000_000,
    }


def test_authentication_service_returns_authenticated_user() -> None:
    service = AuthenticationService(
        build_settings(),
        token_verifier=lambda token: {"claims": valid_claims()},
    )

    user = service.authenticate_access_token("verified-token")

    assert user.id == UUID(USER_ID)
    assert user.email == "user@example.com"
    assert user.role == "authenticated"
    assert user.claims["sub"] == USER_ID


def test_authentication_service_rejects_invalid_token() -> None:
    def verifier(token: str):
        raise AuthInvalidJwtError("Invalid JWT signature")

    service = AuthenticationService(build_settings(), token_verifier=verifier)

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_access_token("invalid-token")

    assert exc_info.value.code == "invalid_access_token"


def test_authentication_service_rejects_expired_token() -> None:
    def verifier(token: str):
        raise AuthInvalidJwtError("JWT has expired")

    service = AuthenticationService(build_settings(), token_verifier=verifier)

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_access_token("expired-token")

    assert exc_info.value.code == "expired_access_token"


def test_authentication_service_rejects_invalid_issuer() -> None:
    claims = valid_claims()
    claims["iss"] = "https://wrong.example/auth/v1"
    service = AuthenticationService(
        build_settings(),
        token_verifier=lambda token: {"claims": claims},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_access_token("token")

    assert exc_info.value.code == "invalid_access_token"


def test_authentication_service_rejects_invalid_audience() -> None:
    claims = valid_claims()
    claims["aud"] = "wrong-audience"
    service = AuthenticationService(
        build_settings(),
        token_verifier=lambda token: {"claims": claims},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_access_token("token")

    assert exc_info.value.code == "invalid_access_token"


def test_authentication_service_rejects_missing_subject() -> None:
    claims = valid_claims()
    claims.pop("sub")
    service = AuthenticationService(
        build_settings(),
        token_verifier=lambda token: {"claims": claims},
    )

    with pytest.raises(AuthenticationError) as exc_info:
        service.authenticate_access_token("token")

    assert exc_info.value.code == "invalid_access_token"


def test_authentication_logs_do_not_include_token(caplog) -> None:
    raw_token = "very-sensitive-jwt"
    service = AuthenticationService(
        build_settings(),
        token_verifier=lambda token: {"claims": valid_claims()},
    )

    with caplog.at_level(logging.INFO):
        service.authenticate_access_token(raw_token)

    assert raw_token not in caplog.text
