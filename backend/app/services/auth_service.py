import logging
from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

from supabase_auth.errors import AuthInvalidJwtError

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.integrations.supabase.client import get_supabase_client
from app.schemas.auth import AuthenticatedUser

logger = logging.getLogger(__name__)


class TokenVerifier(Protocol):
    def __call__(self, token: str) -> Mapping[str, Any] | Any:
        ...


class SupabaseTokenVerifier:
    def __call__(self, token: str) -> Mapping[str, Any] | Any:
        client = get_supabase_client()
        return client.auth.get_claims(token)


class AuthenticationService:
    def __init__(
        self,
        settings: Settings,
        *,
        token_verifier: TokenVerifier | None = None,
    ) -> None:
        self._settings = settings
        self._token_verifier = token_verifier or SupabaseTokenVerifier()

    def authenticate_access_token(self, token: str) -> AuthenticatedUser:
        try:
            response = self._token_verifier(token)
            claims = self._extract_claims(response)
            user = self._build_authenticated_user(claims)
        except AuthenticationError:
            logger.info("authentication_failure")
            raise
        except AuthInvalidJwtError as exc:
            logger.info("authentication_failure")
            raise self._invalid_token_error(exc) from exc
        except Exception as exc:
            logger.info("authentication_failure")
            raise AuthenticationError(
                "Invalid access token.",
                code="invalid_access_token",
            ) from exc

        logger.info(
            "authentication_success",
            extra={"user_id": str(user.id)},
        )
        return user

    def _extract_claims(self, response: Mapping[str, Any] | Any) -> dict[str, Any]:
        claims = response.get("claims") if isinstance(response, Mapping) else None
        if not isinstance(claims, Mapping):
            raise AuthenticationError(
                "Invalid access token.",
                code="invalid_access_token",
            )
        return dict(claims)

    def _build_authenticated_user(self, claims: dict[str, Any]) -> AuthenticatedUser:
        self._validate_claims(claims)

        return AuthenticatedUser(
            id=UUID(str(claims["sub"])),
            email=self._optional_string_claim(claims, "email"),
            role=self._optional_string_claim(claims, "role"),
            claims=claims,
        )

    def _validate_claims(self, claims: dict[str, Any]) -> None:
        expected_issuer = self._settings.jwt_issuer
        if expected_issuer and claims.get("iss") != expected_issuer:
            raise AuthenticationError(
                "Invalid access token.",
                code="invalid_access_token",
            )

        expected_audience = self._settings.jwt_audience
        if expected_audience and not self._audience_matches(
            claims.get("aud"),
            expected_audience,
        ):
            raise AuthenticationError(
                "Invalid access token.",
                code="invalid_access_token",
            )

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationError(
                "Invalid access token.",
                code="invalid_access_token",
            )

        try:
            UUID(subject)
        except ValueError as exc:
            raise AuthenticationError(
                "Invalid access token.",
                code="invalid_access_token",
            ) from exc

    def _audience_matches(self, audience: Any, expected_audience: str) -> bool:
        if isinstance(audience, str):
            return audience == expected_audience
        if isinstance(audience, list):
            return expected_audience in audience
        return False

    def _optional_string_claim(
        self,
        claims: dict[str, Any],
        claim_name: str,
    ) -> str | None:
        value = claims.get(claim_name)
        if isinstance(value, str):
            return value
        return None

    def _invalid_token_error(self, exc: AuthInvalidJwtError) -> AuthenticationError:
        if "expired" in str(exc).lower():
            return AuthenticationError(
                "Access token has expired.",
                code="expired_access_token",
            )
        return AuthenticationError(
            "Invalid access token.",
            code="invalid_access_token",
        )


def get_authentication_service() -> AuthenticationService:
    return AuthenticationService(get_settings())
