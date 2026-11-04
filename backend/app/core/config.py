from functools import lru_cache

from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    app_name: str = Field(default="Private Enterprise AI Platform", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_publishable_key: SecretStr | None = Field(
        default=None,
        alias="SUPABASE_PUBLISHABLE_KEY",
    )
    supabase_secret_key: SecretStr | None = Field(
        default=None,
        alias="SUPABASE_SECRET_KEY",
    )

    jwt_audience: str | None = Field(default=None, alias="JWT_AUDIENCE")
    jwt_issuer: str | None = Field(default=None, alias="JWT_ISSUER")

    document_storage_bucket: str = Field(
        default="enterprise-documents",
        alias="DOCUMENT_STORAGE_BUCKET",
    )
    max_document_file_size: int = Field(
        default=25 * 1024 * 1024,
        alias="MAX_DOCUMENT_FILE_SIZE",
    )
    allowed_document_mime_types: tuple[str, ...] = Field(
        default=(
            "application/pdf",
            "text/plain",
            (
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        ),
        alias="ALLOWED_DOCUMENT_MIME_TYPES",
    )
    embedding_provider: str = Field(default="ollama", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=16, alias="EMBEDDING_BATCH_SIZE")
    embedding_url: str = Field(
        default="http://localhost:11434",
        alias="EMBEDDING_URL",
    )
    embedding_timeout_seconds: float = Field(
        default=30.0,
        alias="EMBEDDING_TIMEOUT_SECONDS",
    )
    qdrant_url: str | None = Field(default=None, alias="QDRANT_URL")
    qdrant_api_key: SecretStr | None = Field(default=None, alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(
        default="enterprise_documents",
        alias="QDRANT_COLLECTION_NAME",
    )
    qdrant_timeout_seconds: float = Field(
        default=30.0,
        alias="QDRANT_TIMEOUT_SECONDS",
    )

    @field_validator("allowed_document_mime_types", mode="before")
    @classmethod
    def parse_allowed_mime_types(cls, value: Any) -> Any:
        if isinstance(value, str):
            return tuple(
                mime_type.strip()
                for mime_type in value.split(",")
                if mime_type.strip()
            )
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized_value = value.strip().lower()
            if normalized_value in {"1", "true", "yes", "on"}:
                return True
            if normalized_value in {"0", "false", "no", "off", "release", ""}:
                return False
        return False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()