from uuid import UUID

from app.services.permission_service import AuthorizationService

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
EMPLOYEE_ROLE_ID = "00000000-0000-0000-0000-000000000003"
MANAGER_ROLE_ID = "00000000-0000-0000-0000-000000000002"
ADMIN_ROLE_ID = "00000000-0000-0000-0000-000000000001"


class FakeQuery:
    def __init__(self, table_name: str, rows: list[dict]) -> None:
        self.table_name = table_name
        self.rows = rows
        self.filters: dict[str, object] = {}

    def select(self, columns: str) -> "FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        self.filters[column] = value
        return self

    def in_(self, column: str, values: list[str]) -> "FakeQuery":
        self.filters[column] = values
        return self

    def execute(self) -> dict[str, list[dict]]:
        rows = self.rows
        for column, expected in self.filters.items():
            if isinstance(expected, list):
                rows = [row for row in rows if row.get(column) in expected]
            else:
                rows = [row for row in rows if row.get(column) == expected]
        return {"data": rows}


class FakeSupabase:
    def __init__(self, *, roles: list[dict], role_permissions: list[dict]) -> None:
        self.rows = {
            "user_roles": roles,
            "role_permissions": role_permissions,
        }

    def table(self, table_name: str) -> FakeQuery:
        return FakeQuery(table_name, self.rows[table_name])


ROLE_ROWS = [
    {
        "user_id": str(USER_ID),
        "role_id": EMPLOYEE_ROLE_ID,
        "roles": {"id": EMPLOYEE_ROLE_ID, "name": "employee"},
    }
]

PERMISSION_ROWS = [
    {
        "role_id": EMPLOYEE_ROLE_ID,
        "permissions": {"name": "profile.read"},
    },
    {
        "role_id": EMPLOYEE_ROLE_ID,
        "permissions": {"name": "documents.read"},
    },
    {
        "role_id": EMPLOYEE_ROLE_ID,
        "permissions": {"name": "chat.use"},
    },
]


def build_service(
    *,
    roles: list[dict] | None = None,
    permissions: list[dict] | None = None,
) -> AuthorizationService:
    return AuthorizationService(
        FakeSupabase(
            roles=roles or ROLE_ROWS,
            role_permissions=permissions or PERMISSION_ROWS,
        )
    )


def test_get_user_roles_returns_role_names() -> None:
    service = build_service()

    assert service.get_user_roles(USER_ID) == ["employee"]
    assert service.has_role(USER_ID, "employee") is True
    assert service.has_role(USER_ID, "admin") is False


def test_employee_permission_boundary() -> None:
    service = build_service()

    assert service.has_permission(USER_ID, "documents.read") is True
    assert service.has_permission(USER_ID, "documents.delete") is False


def test_manager_permission_boundary() -> None:
    service = build_service(
        roles=[
            {
                "user_id": str(USER_ID),
                "role_id": MANAGER_ROLE_ID,
                "roles": {"id": MANAGER_ROLE_ID, "name": "manager"},
            }
        ],
        permissions=[
            {
                "role_id": MANAGER_ROLE_ID,
                "permissions": {"name": "documents.create"},
            }
        ],
    )

    assert service.has_role(USER_ID, "manager") is True
    assert service.has_permission(USER_ID, "documents.create") is True


def test_admin_permission_boundary() -> None:
    service = build_service(
        roles=[
            {
                "user_id": str(USER_ID),
                "role_id": ADMIN_ROLE_ID,
                "roles": {"id": ADMIN_ROLE_ID, "name": "admin"},
            }
        ],
        permissions=[
            {
                "role_id": ADMIN_ROLE_ID,
                "permissions": {"name": "users.manage"},
            }
        ],
    )

    assert service.has_role(USER_ID, "admin") is True
    assert service.has_permission(USER_ID, "users.manage") is True
