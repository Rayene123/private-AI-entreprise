from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthorizationError, ResourceNotFoundError
from app.integrations.storage import StorageService, get_storage_service
from app.integrations.supabase.client import get_service_supabase_client
from app.schemas.document import (
    DocumentCreate,
    DocumentFile,
    DocumentListItem,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.document_file_policy import generate_storage_path, validate_upload
from app.services.permission_service import AuthorizationService

DOCUMENT_COLUMNS = (
    "id,owner_id,department_id,title,description,original_filename,storage_path,"
    "mime_type,file_size_bytes,status,access_level,created_at,updated_at"
)


class DocumentService:
    def __init__(
        self,
        authorization_service: AuthorizationService,
        supabase_client: Any | None = None,
        storage_service: StorageService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._authorization_service = authorization_service
        self._supabase = supabase_client or get_service_supabase_client()
        self._storage_service = storage_service
        self._settings = settings or get_settings()

    @property
    def _storage(self) -> StorageService:
        if self._storage_service is None:
            self._storage_service = get_storage_service()
        return self._storage_service

    def create_document(
        self,
        user_id: UUID,
        document_create: DocumentCreate,
    ) -> DocumentResponse:
        self._require_active_profile_with_permission(user_id, "documents.create")

        payload = document_create.model_dump(mode="json")
        payload.pop("storage_path", None)
        payload["owner_id"] = str(user_id)
        response = (
            self._supabase.table("documents")
            .insert(payload)
            .execute()
        )
        document = self._single_row(response)
        return DocumentResponse(**document)

    def list_documents(self, user_id: UUID) -> list[DocumentListItem]:
        profile = self._require_active_profile_with_permission(
            user_id,
            "documents.read",
        )

        explicit_document_ids = self._get_explicit_document_ids(user_id)
        filters = [
            f"owner_id.eq.{user_id}",
            "access_level.eq.organization",
        ]
        department_id = profile.get("department_id")
        if department_id:
            filters.append(
                f"and(access_level.eq.department,department_id.eq.{department_id})"
            )
        if explicit_document_ids:
            filters.append(f"id.in.({','.join(explicit_document_ids)})")

        query = (
            self._supabase.table("documents")
            .select(DOCUMENT_COLUMNS)
            .eq("status", "active")
            .or_(",".join(filters))
        )

        return [
            DocumentListItem(**self._to_list_item_row(row))
            for row in self._list_rows(query.execute())
        ]

    def get_document(self, user_id: UUID, document_id: UUID) -> DocumentResponse:
        profile = self._require_active_profile_with_permission(
            user_id,
            "documents.read",
        )
        document = self._get_document_row(document_id)
        self._require_document_access(user_id, profile, document)
        return DocumentResponse(**document)

    def update_document(
        self,
        user_id: UUID,
        document_id: UUID,
        document_update: DocumentUpdate,
    ) -> DocumentResponse:
        profile = self._require_active_profile_with_permission(
            user_id,
            "documents.update",
        )
        document = self._get_document_row(document_id)
        self._require_document_access(user_id, profile, document)

        updates = document_update.model_dump(
            exclude_unset=True,
            exclude_none=True,
            mode="json",
        )
        updates.pop("storage_path", None)
        if not updates:
            return DocumentResponse(**document)

        response = (
            self._supabase.table("documents")
            .update(updates)
            .eq("id", str(document_id))
            .execute()
        )
        updated = self._single_row(response)
        return DocumentResponse(**updated)

    def delete_document(self, user_id: UUID, document_id: UUID) -> None:
        profile = self._require_active_profile_with_permission(
            user_id,
            "documents.delete",
        )
        document = self._get_document_row(document_id)
        self._require_document_access(user_id, profile, document)

        if str(document.get("owner_id")) != str(user_id) and not (
            self._authorization_service.has_role(user_id, "admin")
        ):
            raise AuthorizationError(
                "You do not have permission to delete this document.",
                code="document_delete_forbidden",
            )

        (
            self._supabase.table("documents")
            .update({"status": "archived"})
            .eq("id", str(document_id))
            .execute()
        )

    def upload_document_file(
        self,
        user_id: UUID,
        document_id: UUID,
        *,
        filename: str | None,
        content_type: str | None,
        content: bytes,
    ) -> DocumentResponse:
        profile = self._require_active_profile_with_permission(
            user_id,
            "documents.update",
        )
        document = self._get_document_row(document_id)
        self._require_document_access(user_id, profile, document)

        validated = validate_upload(
            filename=filename,
            content_type=content_type,
            content=content,
            settings=self._settings,
        )
        storage_path = generate_storage_path(document_id, validated.original_filename)
        previous_storage_path = document.get("storage_path")

        # Upload the new object first; only touch metadata (and the old
        # object) once the new object is safely stored.
        self._storage.upload(storage_path, validated.content, validated.mime_type)

        try:
            response = (
                self._supabase.table("documents")
                .update(
                    {
                        "storage_path": storage_path,
                        "original_filename": validated.original_filename,
                        "mime_type": validated.mime_type,
                        "file_size_bytes": validated.size_bytes,
                    }
                )
                .eq("id", str(document_id))
                .execute()
            )
            updated = self._single_row(response)
        except Exception:
            # Metadata never ended up pointing at the new object, so remove
            # it rather than leaving an orphaned upload behind.
            self._storage.remove(storage_path)
            raise

        if previous_storage_path and previous_storage_path != storage_path:
            self._storage.remove(previous_storage_path)

        return DocumentResponse(**updated)

    def download_document_file(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> DocumentFile:
        profile = self._require_active_profile_with_permission(
            user_id,
            "documents.read",
        )
        document = self._get_document_row(document_id)

        # Archived documents are not accessible through the normal file
        # endpoint. Treat them the same as "not found" so archival status
        # is not revealed to callers who otherwise lack access.
        if document.get("status") != "active":
            raise ResourceNotFoundError(
                "Document was not found.",
                code="document_not_found",
            )

        self._require_document_access(user_id, profile, document)

        storage_path = document.get("storage_path")
        if not storage_path:
            raise ResourceNotFoundError(
                "This document has no file uploaded.",
                code="document_file_not_found",
            )

        content = self._storage.download(storage_path)
        return DocumentFile(
            content=content,
            mime_type=document.get("mime_type") or "application/octet-stream",
            filename=document.get("original_filename") or "document",
        )

    def _require_active_profile_with_permission(
        self,
        user_id: UUID,
        permission_name: str,
    ) -> dict[str, Any]:
        self._authorization_service.require_permission(user_id, permission_name)
        profile = self._get_profile(user_id)
        if not profile.get("is_active", False):
            raise AuthorizationError(
                "Application profile is inactive.",
                code="inactive_profile",
            )
        return profile

    def _require_document_access(
        self,
        user_id: UUID,
        profile: dict[str, Any],
        document: dict[str, Any],
    ) -> None:
        if not self.can_access_document(user_id, profile, document):
            raise AuthorizationError(
                "You do not have permission to access this document.",
                code="document_access_denied",
            )

    def can_access_document(
        self,
        user_id: UUID,
        profile: dict[str, Any],
        document: dict[str, Any],
    ) -> bool:
        if str(document.get("owner_id")) == str(user_id):
            return True
        if self._has_explicit_access(user_id, UUID(str(document["id"]))):
            return True

        access_level = document.get("access_level")
        if access_level == "organization":
            return True

        if access_level == "department":
            user_department_id = profile.get("department_id")
            document_department_id = document.get("department_id")
            return (
                user_department_id is not None
                and document_department_id is not None
                and str(user_department_id) == str(document_department_id)
            )

        return False

    def _get_profile(self, user_id: UUID) -> dict[str, Any]:
        response = (
            self._supabase.table("profiles")
            .select("id,department_id,is_active")
            .eq("id", str(user_id))
            .limit(1)
            .execute()
        )
        data = self._list_rows(response)
        if not data:
            raise ResourceNotFoundError(
                "Application profile was not found.",
                code="profile_not_found",
            )
        return data[0]

    def _get_document_row(self, document_id: UUID) -> dict[str, Any]:
        response = (
            self._supabase.table("documents")
            .select(DOCUMENT_COLUMNS)
            .eq("id", str(document_id))
            .limit(1)
            .execute()
        )
        data = self._list_rows(response)
        if not data:
            raise ResourceNotFoundError(
                "Document was not found.",
                code="document_not_found",
            )
        return data[0]

    def _get_explicit_document_ids(self, user_id: UUID) -> list[str]:
        response = (
            self._supabase.table("document_user_access")
            .select("document_id")
            .eq("user_id", str(user_id))
            .execute()
        )
        return [
            str(row["document_id"])
            for row in self._list_rows(response)
            if row.get("document_id") is not None
        ]

    def _has_explicit_access(self, user_id: UUID, document_id: UUID) -> bool:
        response = (
            self._supabase.table("document_user_access")
            .select("document_id")
            .eq("document_id", str(document_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        return bool(self._list_rows(response))

    def _single_row(self, response: Any) -> dict[str, Any]:
        rows = self._list_rows(response)
        if not rows:
            raise ResourceNotFoundError(
                "Document was not found.",
                code="document_not_found",
            )
        return rows[0]

    def _list_rows(self, response: Any) -> list[dict[str, Any]]:
        data = response.get("data") if isinstance(response, dict) else response.data
        if data is None:
            return []
        if not isinstance(data, list):
            return []
        return [row for row in data if isinstance(row, dict)]

    def _to_list_item_row(self, row: dict[str, Any]) -> dict[str, Any]:
        list_row = dict(row)
        list_row.pop("storage_path", None)
        return list_row


def get_document_service(
    authorization_service: AuthorizationService,
) -> DocumentService:
    return DocumentService(authorization_service)