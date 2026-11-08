import hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from scripts import ingest_corporate_dataset as runner


OWNER_ID = UUID("11111111-1111-1111-1111-111111111111")


def inventory_row(index: int = 1) -> dict[str, str]:
    path = f"datasets/corporate/raw/hr/policy-{index}.pdf"
    return {
        "document_id": f"CORP-HR-{index:03d}",
        "filename": Path(path).name,
        "relative_path": path,
        "source_organization": "Example University",
        "source_url": "https://example.edu/policy.pdf",
        "department": "hr",
        "document_type": "policy",
        "language": "English",
        "page_count": "1",
        "file_size_bytes": "8",
        "publication_date": "2026-01-01",
        "revision_date": "",
        "quality": "Good",
        "rag_suitability": "High",
        "access_level": "organization",
        "source_type": "public_external",
        "ingestion_status": "not_ingested",
        "notes": "Synthetic test fixture",
    }


def valid_rows(tmp_path, monkeypatch) -> list[dict[str, str]]:
    rows = [inventory_row(index) for index in range(1, 7)]
    for index, row in enumerate(rows):
        row["department"] = ("hr", "hr", "it", "it", "finance", "finance")[index]
        path = tmp_path / row["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-1.4")
        row["file_size_bytes"] = "8"
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    return rows


def test_valid_six_document_inventory(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)

    runner._validate_inventory(rows)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("filename", "different.pdf"),
        ("source_url", "http://example.edu/policy.pdf"),
        ("source_organization", ""),
        ("department", "legal"),
        ("access_level", "invalid"),
        ("source_type", "internal"),
        ("publication_date", "not-a-date"),
    ],
)
def test_inventory_rejects_invalid_metadata(
    monkeypatch,
    tmp_path,
    field: str,
    value: str,
) -> None:
    rows = valid_rows(tmp_path, monkeypatch)
    rows[0][field] = value

    with pytest.raises(ValueError):
        runner._validate_inventory(rows)


def test_inventory_rejects_missing_file_size_and_duplicate_id(
    monkeypatch,
    tmp_path,
) -> None:
    rows = valid_rows(tmp_path, monkeypatch)
    rows[0]["file_size_bytes"] = "99"
    with pytest.raises(ValueError):
        runner._validate_inventory(rows)

    rows = valid_rows(tmp_path, monkeypatch)
    rows[1]["document_id"] = rows[0]["document_id"]
    with pytest.raises(ValueError):
        runner._validate_inventory(rows)


def test_inventory_rejects_filename_mismatch(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)
    rows[0]["relative_path"] = "datasets/corporate/raw/hr/other.pdf"

    with pytest.raises(ValueError, match="filename mismatch"):
        runner._validate_inventory(rows)


def test_inventory_rejects_missing_pdf(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)
    (tmp_path / rows[0]["relative_path"]).unlink()

    with pytest.raises(FileNotFoundError):
        runner._validate_inventory(rows)


def test_inventory_rejects_duplicate_dataset_id(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)
    rows[0]["document_id"] = rows[1]["document_id"]

    with pytest.raises(ValueError, match="duplicate"):
        runner._validate_inventory(rows)


def test_owner_id_is_required_and_must_be_uuid(monkeypatch) -> None:
    monkeypatch.delenv("DATASET_INGESTION_OWNER_ID", raising=False)
    with pytest.raises(RuntimeError, match="required"):
        runner._required_owner_id()

    monkeypatch.setenv("DATASET_INGESTION_OWNER_ID", "not-a-uuid")
    with pytest.raises(RuntimeError, match="not a UUID"):
        runner._required_owner_id()


def test_existing_document_with_changed_hash_is_rejected(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)

    class Documents:
        def find_by_dataset_id(self, dataset_id):
            return SimpleNamespace(
                id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                source_metadata={"source_hash": "0" * 64},
            )

    result = runner._ingest_row(
        rows[0],
        owner_id=OWNER_ID,
        departments={name: OWNER_ID for name in runner.REQUIRED_DEPARTMENTS},
        documents=Documents(),
        indexer=object(),
    )

    assert result["status"] == "failed"
    assert result["stage"] == "existing_record_validation"
    assert result["error_code"] == "existing_record_validation_failed"


def test_upload_failure_cleans_only_new_document(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)

    class Documents:
        def __init__(self):
            self.cleaned = []

        def find_by_dataset_id(self, dataset_id):
            return None

        def create_document(self, owner_id, document):
            return SimpleNamespace(
                id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            )

        def upload_document_file(self, *args, **kwargs):
            raise RuntimeError("provider response with secret")

        def cleanup_created_document(self, owner_id, document_id):
            self.cleaned.append(document_id)

    class Indexer:
        pass

    documents = Documents()
    result = runner._ingest_row(
        rows[0],
        owner_id=OWNER_ID,
        departments={name: OWNER_ID for name in runner.REQUIRED_DEPARTMENTS},
        documents=documents,
        indexer=Indexer(),
    )

    assert result["stage"] == "storage_upload"
    assert documents.cleaned == [UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")]


def test_document_creation_failure_creates_no_cleanup_resource(
    monkeypatch,
    tmp_path,
) -> None:
    rows = valid_rows(tmp_path, monkeypatch)

    class Documents:
        def find_by_dataset_id(self, dataset_id):
            return None

        def create_document(self, owner_id, document):
            raise RuntimeError("database provider response with secret")

    result = runner._ingest_row(
        rows[0],
        owner_id=OWNER_ID,
        departments={name: OWNER_ID for name in runner.REQUIRED_DEPARTMENTS},
        documents=Documents(),
        indexer=object(),
    )

    assert result["status"] == "failed"
    assert result["stage"] == "document_creation"
    assert result["cleanup_status"] == "not_required"


def test_indexing_failure_cleans_new_index_and_document(monkeypatch, tmp_path) -> None:
    rows = valid_rows(tmp_path, monkeypatch)

    class Documents:
        def __init__(self):
            self.cleaned = []

        def find_by_dataset_id(self, dataset_id):
            return None

        def create_document(self, owner_id, document):
            return SimpleNamespace(
                id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            )

        def upload_document_file(self, *args, **kwargs):
            return None

        def set_source_metadata(self, *args, **kwargs):
            return None

        def cleanup_created_document(self, owner_id, document_id):
            self.cleaned.append(document_id)

    class Indexer:
        def __init__(self):
            self.cleaned = []

        def index(self, *args, **kwargs):
            raise RuntimeError("qdrant response with secret")

        def cleanup_created_index(self, document_id):
            self.cleaned.append(document_id)

    documents = Documents()
    indexer = Indexer()
    result = runner._ingest_row(
        rows[0],
        owner_id=OWNER_ID,
        departments={name: OWNER_ID for name in runner.REQUIRED_DEPARTMENTS},
        documents=documents,
        indexer=indexer,
    )

    document_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert result["stage"] == "indexing"
    assert indexer.cleaned == [document_id]
    assert documents.cleaned == [document_id]


def test_existing_indexed_document_is_preserved_and_skipped(
    monkeypatch,
    tmp_path,
) -> None:
    rows = valid_rows(tmp_path, monkeypatch)
    (tmp_path / rows[0]["relative_path"]).write_bytes(b"0" * 8)

    source_hash = hashlib.sha256(b"0" * 8).hexdigest()

    class Documents:
        def find_by_dataset_id(self, dataset_id):
            return SimpleNamespace(
                id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                source_metadata={
                    "source_hash": source_hash,
                    "ingestion_status": "indexed",
                    "chunk_count": 3,
                },
            )

    result = runner._ingest_row(
        rows[0],
        owner_id=OWNER_ID,
        departments={name: OWNER_ID for name in runner.REQUIRED_DEPARTMENTS},
        documents=Documents(),
        indexer=object(),
    )

    assert result["status"] == "skipped"
    assert result["chunk_count"] == 3


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, columns):
        return self

    def eq(self, column, value):
        return self

    def limit(self, count):
        return self

    def execute(self):
        return {"data": self.rows}


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return FakeQuery(self.rows)


class FakeAuthorization:
    def __init__(self, permissions):
        self.permissions = permissions

    def get_user_permissions(self, user_id):
        return list(self.permissions)


def test_owner_preflight_rejects_inactive_and_missing_permissions() -> None:
    inactive = FakeClient([{"id": str(OWNER_ID), "is_active": False}])
    with pytest.raises(RuntimeError, match="inactive"):
        runner._preflight_owner(
            OWNER_ID,
            inactive,
            FakeAuthorization(runner.REQUIRED_OWNER_PERMISSIONS),
        )

    active = FakeClient([{"id": str(OWNER_ID), "is_active": True}])
    with pytest.raises(RuntimeError, match="lacks"):
        runner._preflight_owner(
            OWNER_ID,
            active,
            FakeAuthorization({"documents.read"}),
        )


def test_owner_preflight_rejects_unknown_owner() -> None:
    with pytest.raises(RuntimeError, match="not found"):
        runner._preflight_owner(
            OWNER_ID,
            FakeClient([]),
            FakeAuthorization(runner.REQUIRED_OWNER_PERMISSIONS),
        )


@pytest.mark.parametrize(
    "missing_permission",
    sorted(runner.REQUIRED_OWNER_PERMISSIONS),
)
def test_owner_preflight_requires_each_permission(missing_permission: str) -> None:
    active = FakeClient([{"id": str(OWNER_ID), "is_active": True}])
    permissions = runner.REQUIRED_OWNER_PERMISSIONS - {missing_permission}

    with pytest.raises(RuntimeError, match="lacks"):
        runner._preflight_owner(
            OWNER_ID,
            active,
            FakeAuthorization(permissions),
        )


def test_failure_report_excludes_exception_details(tmp_path, monkeypatch) -> None:
    result: dict = {"dataset_id": "CORP-HR-001", "status": "failed"}
    runner._record_failure(
        result,
        "CORP-HR-001",
        "indexing",
        RuntimeError("secret-token-and-connection-string"),
        "completed",
    )
    monkeypatch.setattr(runner, "REPORT_PATH", tmp_path / "report.md")
    runner._write_report([result])

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "secret-token" not in report
    assert "connection-string" not in report
    assert "indexing_failed" in report


def test_cleanup_failure_is_reported_without_raw_details() -> None:
    class Documents:
        def cleanup_created_document(self, owner_id, document_id):
            raise RuntimeError("private storage response")

    class Indexer:
        def cleanup_created_index(self, document_id):
            raise RuntimeError("qdrant secret response")

    status = runner._cleanup_created_resources(
        OWNER_ID,
        UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        Documents(),
        Indexer(),
    )

    assert status == "manual_intervention_required:index_cleanup,document_cleanup"
