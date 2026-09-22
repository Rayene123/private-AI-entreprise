import logging
import logging.config
from contextvars import ContextVar, Token
from collections.abc import MutableMapping
from typing import Any


request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

SENSITIVE_FIELDS = {
    "access_token",
    "anon_key",
    "authorization",
    "api_key",
    "credential",
    "jwt",
    "password",
    "publishable_key",
    "refresh_token",
    "secret",
    "secret_key",
    "service_role",
    "token",
}


class SensitiveDataFilter(logging.Filter):
    """Redact common sensitive fields from structured log extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get() or "-"

        for key, value in record.__dict__.items():
            if self._is_sensitive_key(key):
                setattr(record, key, "[REDACTED]")
            elif isinstance(value, MutableMapping):
                setattr(record, key, self._redact_mapping(value))
        return True

    def _redact_mapping(self, value: MutableMapping[str, Any]) -> dict[str, Any]:
        return {
            key: "[REDACTED]" if self._is_sensitive_key(str(key)) else item
            for key, item in value.items()
        }

    def _is_sensitive_key(self, key: str) -> bool:
        normalized_key = key.lower()
        return any(sensitive in normalized_key for sensitive in SENSITIVE_FIELDS)


def configure_logging(log_level: str) -> None:
    level = log_level.upper()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "sensitive_data": {
                    "()": SensitiveDataFilter,
                },
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["sensitive_data"],
                },
            },
            "root": {
                "handlers": ["console"],
                "level": level,
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
            },
        }
    )


def set_request_id(request_id: str) -> Token[str | None]:
    return request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    request_id_context.reset(token)
