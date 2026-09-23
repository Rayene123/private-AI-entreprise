from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.exceptions import AuthorizationError
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.document_service import DocumentService

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


class FakeSupabase:
    def __init__(
        self,
        *,
        profiles: list[dict],
        documents: list[dict],
        document_user_access: list[dict] | None = None,
    ) -> None:
        self.next_document_id = DOCUMENT_ID
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
) -> DocumentService:
    return DocumentService(
        FakeAuthorizationService(permissions, roles),
        FakeSupabase(
            profiles=profiles or [profile()],
            documents=documents or [],
            document_user_access=access_rows,
        ),
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
