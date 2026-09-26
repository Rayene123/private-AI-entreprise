import logging
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import IntegrationUnavailableError
from app.integrations.supabase.client import get_service_supabase_client

logger = logging.getLogger(__name__)


class StorageObjectError(IntegrationUnavailableError):
    """Raised when the storage provider cannot complete an object operation."""

    code = "storage_unavailable"
    message = "The document storage service is temporarily unavailable."


class StorageService:
    """Thin boundary over Supabase Storage for enterprise document objects.

    This intentionally only exposes the small set of operations Module 6
    needs (upload/download/remove) against a single private bucket. It does
    not perform authorization; callers must authorize the operation before
    calling this service.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        supabase_client: Any | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._supabase = supabase_client or get_service_supabase_client()

    @property
    def bucket_name(self) -> str:
        return self._settings.document_storage_bucket

    def upload(self, storage_path: str, file_bytes: bytes, mime_type: str) -> None:
        try:
            self._bucket().upload(
                storage_path,
                file_bytes,
                file_options={
                    "content-type": mime_type,
                    "upsert": "true",
                },
            )
        except Exception as exc:
            logger.warning(
                "document_storage_upload_failed",
                extra={"storage_bucket": self.bucket_name},
            )
            raise StorageObjectError(
                "The document could not be stored.",
                code="storage_upload_failed",
            ) from exc

    def download(self, storage_path: str) -> bytes:
        try:
            return self._bucket().download(storage_path)
        except Exception as exc:
            logger.warning(
                "document_storage_download_failed",
                extra={"storage_bucket": self.bucket_name},
            )
            raise StorageObjectError(
                "The document could not be retrieved.",
                code="storage_download_failed",
            ) from exc

    def remove(self, storage_path: str) -> None:
        try:
            self._bucket().remove([storage_path])
        except Exception:
            # Best-effort cleanup: an orphaned/leftover object is preferable
            # to surfacing a cleanup failure as a request error, and no
            # sensitive details are logged.
            logger.warning(
                "document_storage_remove_failed",
                extra={"storage_bucket": self.bucket_name},
            )

    def _bucket(self) -> Any:
        return self._supabase.storage.from_(self.bucket_name)


def get_storage_service() -> StorageService:
    return StorageService()