from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.exceptions import AuthorizationError, ResourceNotFoundError
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.document_service import DocumentService

PDF_BYTES = b"%PDF-1.4\n%mock pdf content"

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
ADMIN_ID = UUID("33333333-3333-3333-3333-333333333333")
DOCUMENT_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EXPLICIT_DOCUMENT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DEPARTMENT_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
OTHER_DEPARTMENT_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
NOW = datetime(2026, 9, 23, tzinfo=UTC).isoformat()


def document_row(**overrides) -> dict:
    row = {
        "id": str(DOCUMENT_ID),
        "owner_id": str(USER_ID),
        "department_id": str(DEPARTMENT_ID),
        "title": "Policy",
        "description": "Internal policy",
        "original_filename": "policy.pdf",
        "storage_path": None,
        "mime_type": "application/pdf",
        "file_size_bytes": 100,
        "status": "active",
        "access_level": "department",
        "created_at": NOW,
        "updated_at": NOW,
    }
    row.update(overrides)
    return row


class FakeAuthorizationService:
    def __init__(
        self,
        permissions: set[str],
        roles: set[str] | None = None,
    ) -> None:
        self.permissions = permissions
        self.roles = roles or set()

    def require_permission(self, user_id: UUID, permission_name: str) -> None:
        if permission_name not in self.permissions:
            raise AuthorizationError(
                "You do not have permission to perform this action.",
                code="insufficient_permissions",
            )

    def has_role(self, user_id: UUID, role_name: str) -> bool:
        return role_name in self.roles


class FakeQuery:
    def __init__(self, supabase: "FakeSupabase", table_name: str) -> None:
        self.supabase = supabase
        self.table_name = table_name
        self.filters: dict[str, object] = {}
        self.limit_count: int | None = None
        self.insert_payload: dict | None = None
        self.update_payload: dict | None = None
        self.or_filter: str | None = None

    def select(self, columns: str) -> "FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        self.filters[column] = value
        return self

    def limit(self, count: int) -> "FakeQuery":
        self.limit_count = count
        return self

    def or_(self, value: str) -> "FakeQuery":
        self.or_filter = value
        return self

    def insert(self, payload: dict) -> "FakeQuery":
        self.insert_payload = payload
        return self

    def update(self, payload: dict) -> "FakeQuery":
        self.update_payload = payload
        return self

    def execute(self) -> dict[str, list[dict]]:
        if self.insert_payload is not None:
            row = document_row(
                id=str(self.supabase.next_document_id),
                created_at=NOW,
                updated_at=NOW,
                **self.insert_payload,
            )
            self.supabase.rows["documents"].append(row)
            return {"data": [row]}

        rows = list(self.supabase.rows[self.table_name])
        for column, expected in self.filters.items():
            rows = [row for row in rows if str(row.get(column)) == str(expected)]

        if self.or_filter is not None:
            rows = self._apply_or_filter(rows)

        if self.update_payload is not None:
            if self.table_name == "documents" and self.supabase.fail_metadata_update:
                raise RuntimeError("metadata update failed")
            for row in rows:
                row.update(self.update_payload)
                row["updated_at"] = NOW
            return {"data": rows[:1]}

        if self.limit_count is not None:
            rows = rows[: self.limit_count]
        return {"data": rows}

    def _apply_or_filter(self, rows: list[dict]) -> list[dict]:
        clauses = self.or_filter or ""
        allowed: list[dict] = []
        for row in rows:
            row_id = str(row.get("id"))
            if f"owner_id.eq.{row.get('owner_id')}" in clauses:
                allowed.append(row)
                continue
            if "access_level.eq.organization" in clauses and (
                row.get("access_level") == "organization"
            ):
                allowed.append(row)
                continue
            if (
                "and(access_level.eq.department" in clauses
                and row.get("access_level") == "department"
                and f"department_id.eq.{row.get('department_id')}" in clauses
            ):
                allowed.append(row)
                continue
            if row_id in clauses:
                allowed.append(row)
        return allowed


class FakeStorageService:
    """Records storage operations without touching real Supabase Storage."""

    def __init__(self, *, fail_upload: bool = False) -> None:
        self.fail_upload = fail_upload
        self.uploaded: dict[str, tuple[bytes, str]] = {}
        self.removed: list[str] = []
        self.upload_calls = 0
        self.download_calls: list[str] = []

    def upload(self, storage_path: str, file_bytes: bytes, mime_type: str) -> None:
        self.upload_calls += 1
        if self.fail_upload:
            raise RuntimeError("storage upload failed")
        self.uploaded[storage_path] = (file_bytes, mime_type)

    def download(self, storage_path: str) -> bytes:
        self.download_calls.append(storage_path)
        if storage_path not in self.uploaded:
            raise RuntimeError("storage download failed")
        return self.uploaded[storage_path][0]

    def remove(self, storage_path: str) -> None:
        self.removed.append(storage_path)
        self.uploaded.pop(storage_path, None)


class FakeSupabase:
    def __init__(
        self,
        *,
        profiles: list[dict],
        documents: list[dict],
        document_user_access: list[dict] | None = None,
        fail_metadata_update: bool = False,
    ) -> None:
        self.next_document_id = DOCUMENT_ID
        self.fail_metadata_update = fail_metadata_update
        self.rows = {
            "profiles": profiles,
            "documents": documents,
            "document_user_access": document_user_access or [],
        }

    def table(self, table_name: str) -> FakeQuery:
        return FakeQuery(self, table_name)


def profile(
    user_id: UUID = USER_ID,
    department_id: UUID | None = DEPARTMENT_ID,
    is_active: bool = True,
) -> dict:
    return {
        "id": str(user_id),
        "department_id": str(department_id) if department_id else None,
        "is_active": is_active,
    }


def build_service(
    *,
    permissions: set[str],
    roles: set[str] | None = None,
    profiles: list[dict] | None = None,
    documents: list[dict] | None = None,
    access_rows: list[dict] | None = None,
    storage_service: FakeStorageService | None = None,
    fail_metadata_update: bool = False,
    settings: Settings | None = None,
) -> DocumentService:
    return DocumentService(
        FakeAuthorizationService(permissions, roles),
        FakeSupabase(
            profiles=profiles or [profile()],
            documents=documents or [],
            document_user_access=access_rows,
            fail_metadata_update=fail_metadata_update,
        ),
        storage_service=storage_service,
        settings=settings,
    )


def test_create_document_sets_owner_from_authenticated_user() -> None:
    service = build_service(
        permissions={"documents.create"},
        documents=[],
    )

    created = service.create_document(
        USER_ID,
        DocumentCreate(
            title="HR Policy",
            department_id=DEPARTMENT_ID,
            access_level="department",
        ),
    )

    assert created.owner_id == USER_ID
    assert created.title == "HR Policy"


def test_user_without_read_permission_is_denied() -> None:
    service = build_service(permissions=set(), documents=[document_row()])

    with pytest.raises(AuthorizationError) as exc_info:
        service.get_document(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "insufficient_permissions"


def test_organization_document_allows_user_with_read_permission() -> None:
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="organization")],
    )

    response = service.get_document(USER_ID, DOCUMENT_ID)

    assert response.id == DOCUMENT_ID


def test_department_document_allows_same_department_user() -> None:
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="department")],
    )

    response = service.get_document(USER_ID, DOCUMENT_ID)

    assert response.id == DOCUMENT_ID


def test_department_document_denies_different_department_user() -> None:
    service = build_service(
        permissions={"documents.read"},
        profiles=[profile(department_id=OTHER_DEPARTMENT_ID)],
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="department")],
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.get_document(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "document_access_denied"


def test_private_document_allows_owner() -> None:
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(access_level="private")],
    )

    response = service.get_document(USER_ID, DOCUMENT_ID)

    assert response.id == DOCUMENT_ID


def test_private_document_denies_unrelated_user() -> None:
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="private")],
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.get_document(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "document_access_denied"


def test_private_document_allows_explicitly_authorized_user() -> None:
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="private")],
        access_rows=[
            {"document_id": str(DOCUMENT_ID), "user_id": str(USER_ID)},
        ],
    )

    response = service.get_document(USER_ID, DOCUMENT_ID)

    assert response.id == DOCUMENT_ID


def test_list_documents_returns_only_accessible_active_documents() -> None:
    service = build_service(
        permissions={"documents.read"},
        documents=[
            document_row(title="Owned"),
            document_row(
                id=str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaab")),
                owner_id=str(OTHER_USER_ID),
                title="Organization",
                access_level="organization",
            ),
            document_row(
                id=str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaac")),
                owner_id=str(OTHER_USER_ID),
                title="Same Department",
                access_level="department",
            ),
            document_row(
                id=str(EXPLICIT_DOCUMENT_ID),
                owner_id=str(OTHER_USER_ID),
                title="Explicit",
                access_level="private",
            ),
            document_row(
                id=str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaad")),
                owner_id=str(OTHER_USER_ID),
                title="Archived",
                access_level="organization",
                status="archived",
            ),
            document_row(
                id=str(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaae")),
                owner_id=str(OTHER_USER_ID),
                title="Denied",
                access_level="private",
            ),
        ],
        access_rows=[
            {"document_id": str(EXPLICIT_DOCUMENT_ID), "user_id": str(USER_ID)},
        ],
    )

    documents = service.list_documents(USER_ID)

    assert [document.title for document in documents] == [
        "Owned",
        "Organization",
        "Same Department",
        "Explicit",
    ]


def test_update_requires_document_access() -> None:
    service = build_service(
        permissions={"documents.update"},
        profiles=[profile(department_id=OTHER_DEPARTMENT_ID)],
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="department")],
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.update_document(
            USER_ID,
            DOCUMENT_ID,
            DocumentUpdate(title="Updated"),
        )

    assert exc_info.value.code == "document_access_denied"


def test_authorized_user_can_update_document_metadata() -> None:
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row()],
    )

    response = service.update_document(
        USER_ID,
        DOCUMENT_ID,
        DocumentUpdate(title="Updated"),
    )

    assert response.title == "Updated"
    assert response.owner_id == USER_ID


def test_owner_with_delete_permission_can_archive_document() -> None:
    row = document_row()
    service = build_service(
        permissions={"documents.delete"},
        documents=[row],
    )

    service.delete_document(USER_ID, DOCUMENT_ID)

    assert row["status"] == "archived"


def test_non_owner_cannot_delete_someone_elses_document() -> None:
    service = build_service(
        permissions={"documents.delete"},
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="organization")],
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.delete_document(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "document_delete_forbidden"


def test_admin_with_delete_permission_can_archive_any_accessible_document() -> None:
    row = document_row(owner_id=str(OTHER_USER_ID), access_level="organization")
    service = build_service(
        permissions={"documents.delete"},
        roles={"admin"},
        profiles=[profile(user_id=ADMIN_ID)],
        documents=[row],
    )

    service.delete_document(ADMIN_ID, DOCUMENT_ID)

    assert row["status"] == "archived"


def test_inactive_profile_is_denied() -> None:
    service = build_service(
        permissions={"documents.read"},
        profiles=[profile(is_active=False)],
        documents=[document_row()],
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.get_document(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "inactive_profile"


# --------------------------------------------------------------------------
# Module 6: upload_document_file
# --------------------------------------------------------------------------


def test_authorized_user_can_upload_document_file() -> None:
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
    )

    response = service.upload_document_file(
        USER_ID,
        DOCUMENT_ID,
        filename="policy.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    )

    assert response.storage_path is not None
    assert response.storage_path.startswith(f"documents/{DOCUMENT_ID}/")
    assert response.mime_type == "application/pdf"
    assert response.file_size_bytes == len(PDF_BYTES)
    assert storage.uploaded[response.storage_path][0] == PDF_BYTES


def test_upload_requires_documents_update_permission() -> None:
    storage = FakeStorageService()
    service = build_service(
        permissions=set(),
        documents=[document_row()],
        storage_service=storage,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="policy.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
        )

    assert exc_info.value.code == "insufficient_permissions"
    assert storage.upload_calls == 0


def test_unauthorized_user_cannot_upload_document_file() -> None:
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        profiles=[profile(department_id=OTHER_DEPARTMENT_ID)],
        documents=[document_row(owner_id=str(OTHER_USER_ID), access_level="department")],
        storage_service=storage,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="policy.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
        )

    assert exc_info.value.code == "document_access_denied"
    assert storage.upload_calls == 0


def test_upload_stores_object_before_updating_metadata() -> None:
    # The new object must be durably stored before metadata is repointed at
    # it, so a metadata failure never leaves metadata referencing a file
    # that was never actually uploaded.
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
    )

    response = service.upload_document_file(
        USER_ID,
        DOCUMENT_ID,
        filename="policy.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    )

    assert storage.upload_calls == 1
    assert response.storage_path in storage.uploaded


def test_metadata_updated_only_after_successful_storage_upload() -> None:
    storage = FakeStorageService(fail_upload=True)
    row = document_row(storage_path=None, original_filename="original.pdf")
    service = build_service(
        permissions={"documents.update"},
        documents=[row],
        storage_service=storage,
    )

    with pytest.raises(RuntimeError):
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="policy.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
        )

    assert row["storage_path"] is None
    assert row["original_filename"] == "original.pdf"


def test_storage_failure_does_not_corrupt_metadata() -> None:
    storage = FakeStorageService(fail_upload=True)
    row = document_row(
        storage_path="documents/existing/old.pdf",
        original_filename="original.pdf",
        mime_type="application/pdf",
        file_size_bytes=999,
    )
    service = build_service(
        permissions={"documents.update"},
        documents=[row],
        storage_service=storage,
    )

    with pytest.raises(RuntimeError):
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="new.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
        )

    assert row["storage_path"] == "documents/existing/old.pdf"
    assert row["original_filename"] == "original.pdf"
    assert row["file_size_bytes"] == 999


def test_cleanup_occurs_when_metadata_update_fails() -> None:
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
        fail_metadata_update=True,
    )

    with pytest.raises(RuntimeError):
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="policy.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
        )

    # The newly uploaded object must not be left behind once metadata could
    # not be repointed at it.
    assert storage.removed
    assert not storage.uploaded


def test_old_file_remains_if_replacement_upload_fails() -> None:
    storage = FakeStorageService(fail_upload=True)
    storage.uploaded["documents/existing/old.pdf"] = (b"old content", "application/pdf")
    row = document_row(storage_path="documents/existing/old.pdf")
    service = build_service(
        permissions={"documents.update"},
        documents=[row],
        storage_service=storage,
    )

    with pytest.raises(RuntimeError):
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="new.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
        )

    assert "documents/existing/old.pdf" in storage.uploaded
    assert storage.removed == []


def test_old_file_is_removed_after_successful_replacement() -> None:
    storage = FakeStorageService()
    storage.uploaded["documents/existing/old.pdf"] = (b"old content", "application/pdf")
    row = document_row(storage_path="documents/existing/old.pdf")
    service = build_service(
        permissions={"documents.update"},
        documents=[row],
        storage_service=storage,
    )

    response = service.upload_document_file(
        USER_ID,
        DOCUMENT_ID,
        filename="new.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    )

    assert storage.removed == ["documents/existing/old.pdf"]
    assert response.storage_path != "documents/existing/old.pdf"
    assert "documents/existing/old.pdf" not in storage.uploaded


def test_owner_cannot_be_changed_through_upload() -> None:
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
    )

    response = service.upload_document_file(
        USER_ID,
        DOCUMENT_ID,
        filename="policy.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    )

    assert response.owner_id == USER_ID


def test_upload_storage_path_is_generated_server_side() -> None:
    # DocumentCreate/DocumentUpdate accept a storage_path field, but upload
    # never accepts one from the caller: it is always derived from the
    # authorized document ID.
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
    )

    response = service.upload_document_file(
        USER_ID,
        DOCUMENT_ID,
        filename="policy.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    )

    assert response.storage_path.startswith(f"documents/{DOCUMENT_ID}/")


def test_upload_rejects_unsupported_file() -> None:
    from app.core.exceptions import ValidationError

    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.update"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
    )

    with pytest.raises(ValidationError) as exc_info:
        service.upload_document_file(
            USER_ID,
            DOCUMENT_ID,
            filename="script.sh",
            content_type="application/x-sh",
            content=b"#!/bin/sh",
        )

    assert exc_info.value.code == "unsupported_mime_type"
    assert storage.upload_calls == 0


# --------------------------------------------------------------------------
# Module 6: download_document_file
# --------------------------------------------------------------------------


def test_authorized_user_can_download_document_file() -> None:
    storage = FakeStorageService()
    storage.uploaded["documents/existing/file.pdf"] = (PDF_BYTES, "application/pdf")
    service = build_service(
        permissions={"documents.read"},
        documents=[
            document_row(
                storage_path="documents/existing/file.pdf",
                original_filename="policy.pdf",
                mime_type="application/pdf",
            )
        ],
        storage_service=storage,
    )

    document_file = service.download_document_file(USER_ID, DOCUMENT_ID)

    assert document_file.content == PDF_BYTES
    assert document_file.mime_type == "application/pdf"
    assert document_file.filename == "policy.pdf"


def test_unauthorized_user_cannot_download_document_file() -> None:
    storage = FakeStorageService()
    storage.uploaded["documents/existing/file.pdf"] = (PDF_BYTES, "application/pdf")
    service = build_service(
        permissions={"documents.read"},
        profiles=[profile(department_id=OTHER_DEPARTMENT_ID)],
        documents=[
            document_row(
                owner_id=str(OTHER_USER_ID),
                access_level="department",
                storage_path="documents/existing/file.pdf",
            )
        ],
        storage_service=storage,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        service.download_document_file(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "document_access_denied"
    assert storage.download_calls == []


def test_download_reuses_document_level_authorization() -> None:
    # Private documents are only downloadable by the owner or an explicitly
    # authorized user, exactly as for metadata reads: the same
    # can_access_document policy is applied.
    storage = FakeStorageService()
    storage.uploaded["documents/existing/file.pdf"] = (PDF_BYTES, "application/pdf")
    service = build_service(
        permissions={"documents.read"},
        documents=[
            document_row(
                owner_id=str(OTHER_USER_ID),
                access_level="private",
                storage_path="documents/existing/file.pdf",
            )
        ],
        access_rows=[{"document_id": str(DOCUMENT_ID), "user_id": str(USER_ID)}],
        storage_service=storage,
    )

    document_file = service.download_document_file(USER_ID, DOCUMENT_ID)

    assert document_file.content == PDF_BYTES


def test_archived_document_cannot_be_downloaded() -> None:
    storage = FakeStorageService()
    storage.uploaded["documents/existing/file.pdf"] = (PDF_BYTES, "application/pdf")
    service = build_service(
        permissions={"documents.read"},
        documents=[
            document_row(
                storage_path="documents/existing/file.pdf",
                status="archived",
            )
        ],
        storage_service=storage,
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        service.download_document_file(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "document_not_found"
    assert storage.download_calls == []


def test_document_with_no_uploaded_file_returns_not_found() -> None:
    storage = FakeStorageService()
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(storage_path=None)],
        storage_service=storage,
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        service.download_document_file(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "document_file_not_found"


def test_storage_errors_are_translated_safely() -> None:
    from app.integrations.storage import StorageObjectError

    class BrokenStorageService(FakeStorageService):
        def download(self, storage_path: str) -> bytes:
            raise StorageObjectError(
                "The document could not be retrieved.",
                code="storage_download_failed",
            )

    storage = BrokenStorageService()
    service = build_service(
        permissions={"documents.read"},
        documents=[document_row(storage_path="documents/existing/file.pdf")],
        storage_service=storage,
    )

    with pytest.raises(StorageObjectError) as exc_info:
        service.download_document_file(USER_ID, DOCUMENT_ID)

    assert exc_info.value.code == "storage_download_failed"
    # The safe, generic message must never leak provider-internal details.
    assert "supabase" not in exc_info.value.message.lower()
    assert "bucket" not in exc_info.value.message.lower()


def test_download_does_not_expose_sensitive_information() -> None:
    storage = FakeStorageService()
    storage.uploaded["documents/existing/file.pdf"] = (PDF_BYTES, "application/pdf")
    service = build_service(
        permissions={"documents.read"},
        documents=[
            document_row(
                storage_path="documents/existing/file.pdf",
                original_filename="policy.pdf",
            )
        ],
        storage_service=storage,
    )

    document_file = service.download_document_file(USER_ID, DOCUMENT_ID)

    # The response carries only content, MIME type, and display filename:
    # no storage path, credentials, or internal identifiers.
    assert set(vars(document_file).keys()) == {"content", "mime_type", "filename"}