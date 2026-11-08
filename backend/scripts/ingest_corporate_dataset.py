"""Controlled, idempotent ingestion of the inspected corporate reference set.

This runner intentionally persists the six dataset documents. It never deletes
or archives existing records and requires an explicitly selected owner account.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings
from app.integrations.supabase.client import get_service_supabase_client
from app.schemas.document import DocumentCreate
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.document_service import DocumentService
from app.services.permission_service import AuthorizationService

logger = logging.getLogger(__name__)
CSV_PATH = ROOT / "datasets" / "corporate" / "metadata" / "documents.csv"
REPORT_PATH = ROOT / "datasets" / "corporate" / "metadata" / "ingestion-report.md"
REQUIRED_DEPARTMENTS = {"hr", "it", "finance"}
REQUIRED_FIELDS = {
    "document_id",
    "filename",
    "relative_path",
    "source_organization",
    "source_url",
    "department",
    "document_type",
    "language",
    "access_level",
    "source_type",
}
ALLOWED_ACCESS_LEVELS = {"organization", "department", "private"}
REQUIRED_OWNER_PERMISSIONS = {
    "documents.create",
    "documents.update",
    "documents.read",
}


def main() -> int:
    rows = _read_inventory()
    _validate_inventory(rows)
    owner_id = _required_owner_id()
    client = get_service_supabase_client(get_settings())
    departments = _resolve_departments(client)
    authorization = AuthorizationService(supabase_client=client)
    _preflight_owner(owner_id, client, authorization)
    documents = DocumentService(
        authorization,
        supabase_client=client,
    )
    indexer = DocumentIndexingService(
        documents,
        DocumentIngestionService(documents),
    )
    results: list[dict[str, Any]] = []

    for row in rows:
        results.append(
            _ingest_row(
                row,
                owner_id=owner_id,
                departments=departments,
                documents=documents,
                indexer=indexer,
            )
        )

    _write_report(results)
    failures = [result for result in results if result["status"] == "failed"]
    return 1 if failures else 0


def _ingest_row(
    row: dict[str, str],
    *,
    owner_id: UUID,
    departments: dict[str, UUID],
    documents: DocumentService,
    indexer: DocumentIndexingService,
) -> dict[str, Any]:
    dataset_id = row["document_id"]
    path = ROOT / row["relative_path"]
    result: dict[str, Any] = {"dataset_id": dataset_id, "filename": row["filename"]}
    created_document = False
    indexing_started = False
    document_id: UUID | None = None
    stage = "source_read"
    try:
        content = path.read_bytes()
        source_hash = hashlib.sha256(content).hexdigest()
        stage = "existing_record_validation"
        existing = documents.find_by_dataset_id(dataset_id)
        if existing:
            metadata = existing.source_metadata or {}
            existing_hash = metadata.get("source_hash")
            if not existing_hash:
                raise RuntimeError(
                    "existing dataset ID has no stored source hash; "
                    "manual review required"
                )
            if existing_hash and existing_hash != source_hash:
                raise RuntimeError(
                    "existing dataset ID has a different source hash; "
                    "manual review required"
                )
            if metadata.get("ingestion_status") == "indexed":
                result.update(
                    status="skipped",
                    document_id=str(existing.id),
                    source_hash=source_hash,
                    chunk_count=metadata.get("chunk_count", 0),
                )
                return result
            document_id = existing.id
        else:
            department = departments[row["department"].lower()]
            stage = "document_creation"
            document = documents.create_document(
                owner_id,
                DocumentCreate(
                    title=f"{row['source_organization']} — {row['filename']}",
                    description=(
                        f"Public external reference; dataset ID {dataset_id}."
                    ),
                    department_id=department,
                    access_level=row["access_level"],
                    original_filename=row["filename"],
                    mime_type="application/pdf",
                    file_size_bytes=len(content),
                ),
            )
            document_id = document.id
            created_document = True
            stage = "storage_upload"
            documents.upload_document_file(
                owner_id,
                document_id,
                filename=row["filename"],
                content_type="application/pdf",
                content=content,
            )

        base_metadata = {
            key: value
            for key, value in row.items()
            if key != "ingestion_status"
        }
        base_metadata.update(
            {
                "dataset_id": dataset_id,
                "source_hash": source_hash,
                "ingestion_status": "indexing",
            }
        )
        stage = "provenance_persistence"
        documents.set_source_metadata(owner_id, document_id, base_metadata)
        stage = "indexing"
        indexing_started = True
        ingestion = indexer.index(owner_id, document_id)
        stage = "final_verification"
        final_metadata = {
            **base_metadata,
            "ingestion_status": "indexed",
            "chunk_count": ingestion.chunk_count,
            "indexed_count": ingestion.indexed_count,
            "markdown_length": ingestion.markdown_length,
            "file_type": ingestion.file_type,
        }
        documents.set_source_metadata(owner_id, document_id, final_metadata)
        result.update(
            status="indexed",
            document_id=str(document_id),
            source_hash=source_hash,
            chunk_count=ingestion.chunk_count,
        )
    except Exception as exc:
        cleanup_status = "not_required"
        if created_document and document_id is not None:
            cleanup_status = _cleanup_created_resources(
                owner_id,
                document_id,
                documents,
                indexer,
                indexing_started=indexing_started,
            )
        _record_failure(result, dataset_id, stage, exc, cleanup_status)
    return result


def _read_inventory() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _validate_inventory(rows: list[dict[str, str]]) -> None:
    if len(rows) != 6:
        raise ValueError(f"expected six inventory rows, found {len(rows)}")
    ids = [row["document_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("inventory contains duplicate document IDs")
    departments = {row.get("department", "").lower() for row in rows}
    if departments != REQUIRED_DEPARTMENTS:
        raise ValueError("inventory departments do not match HR, IT, and Finance")
    for row in rows:
        missing_fields = [
            field for field in REQUIRED_FIELDS if not row.get(field, "").strip()
        ]
        if missing_fields:
            raise ValueError(
                f"missing required provenance fields for {row.get('document_id', '?')}"
            )
        if Path(row["relative_path"]).name != row["filename"]:
            raise ValueError(f"filename mismatch: {row['document_id']}")
        source_url = urlparse(row["source_url"])
        if source_url.scheme != "https" or not source_url.netloc:
            raise ValueError(f"invalid source URL: {row['document_id']}")
        if row["access_level"].lower() not in ALLOWED_ACCESS_LEVELS:
            raise ValueError(f"invalid access level: {row['document_id']}")
        if row["source_type"] != "public_external":
            raise ValueError(f"invalid source type: {row['document_id']}")
        if row.get("publication_date"):
            try:
                date.fromisoformat(row["publication_date"])
            except ValueError as exc:
                raise ValueError(
                    f"invalid publication date: {row['document_id']}"
                ) from exc
        path = ROOT / row["relative_path"]
        if not path.is_file():
            raise FileNotFoundError(f"missing dataset file: {row['relative_path']}")
        if path.stat().st_size != int(row["file_size_bytes"]):
            raise ValueError(f"file size mismatch: {row['document_id']}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"unsupported dataset file: {row['filename']}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if len(digest) != 64:
            raise ValueError(f"invalid source hash: {row['document_id']}")


def _required_owner_id() -> UUID:
    value = os.getenv("DATASET_INGESTION_OWNER_ID")
    if not value:
        raise RuntimeError(
            "DATASET_INGESTION_OWNER_ID is required; no existing account was selected"
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise RuntimeError("DATASET_INGESTION_OWNER_ID is not a UUID") from exc


def _resolve_departments(client: Any) -> dict[str, UUID]:
    response = client.table("departments").select("id,name").execute()
    data = response.data if hasattr(response, "data") else response.get("data", [])
    resolved = {
        str(row["name"]).strip().lower(): UUID(str(row["id"]))
        for row in data or []
        if row.get("name") and row.get("id")
    }
    missing = REQUIRED_DEPARTMENTS - resolved.keys()
    if missing:
        raise RuntimeError(
            "required departments are missing: " + ", ".join(sorted(missing))
        )
    return {name: resolved[name] for name in REQUIRED_DEPARTMENTS}


def _preflight_owner(
    owner_id: UUID,
    client: Any,
    authorization: AuthorizationService,
) -> None:
    response = (
        client.table("profiles")
        .select("id,is_active")
        .eq("id", str(owner_id))
        .limit(1)
        .execute()
    )
    data = response.data if hasattr(response, "data") else response.get("data", [])
    if not data:
        raise RuntimeError("dataset ingestion owner was not found")
    if not data[0].get("is_active"):
        raise RuntimeError("dataset ingestion owner is inactive")
    permissions = set(authorization.get_user_permissions(owner_id))
    missing = REQUIRED_OWNER_PERMISSIONS - permissions
    if missing:
        raise RuntimeError("dataset ingestion owner lacks required permissions")


def _cleanup_created_resources(
    owner_id: UUID,
    document_id: UUID,
    documents: DocumentService,
    indexer: DocumentIndexingService,
    *,
    indexing_started: bool = True,
) -> str:
    failures: list[str] = []
    if indexing_started:
        try:
            indexer.cleanup_created_index(document_id)
        except Exception:
            logger.exception(
                "corporate_dataset_index_cleanup_failed",
                extra={"document_id": str(document_id)},
            )
            failures.append("index_cleanup")
    try:
        documents.cleanup_created_document(owner_id, document_id)
    except Exception:
        logger.exception(
            "corporate_dataset_document_cleanup_failed",
            extra={"document_id": str(document_id)},
        )
        failures.append("document_cleanup")
    return "manual_intervention_required:" + ",".join(failures) if failures else "completed"


def _record_failure(
    result: dict[str, Any],
    dataset_id: str,
    stage: str,
    exc: Exception,
    cleanup_status: str,
) -> None:
    error_code = getattr(exc, "code", None) or f"{stage}_failed"
    logger.exception(
        "corporate_dataset_ingestion_failed",
        extra={
            "dataset_id": dataset_id,
            "processing_stage": stage,
            "error_code": error_code,
        },
    )
    result.update(
        status="failed",
        error_code=error_code,
        stage=stage,
        cleanup_status=cleanup_status,
    )


def _write_report(results: list[dict[str, Any]]) -> None:
    lines = [
        "# Corporate dataset ingestion report",
        "",
        "This report is generated by `backend/scripts/ingest_corporate_dataset.py`.",
        "The runner uses `DocumentService` and `DocumentIndexingService`; it does",
        "not write directly to Qdrant or bypass document authorization.",
        "",
        "| Dataset ID | Status | Document ID | Chunks |",
        "|---|---|---|---:|",
    ]
    for result in results:
        lines.append(
            f"| {result['dataset_id']} | {result['status']} | "
            f"{result.get('document_id', '')} | {result.get('chunk_count', '')} |"
        )
        if result.get("error_code"):
            lines.append(
                f"\n- `{result['dataset_id']}`: "
                f"stage `{result.get('stage', 'unknown')}`, "
                f"code `{result['error_code']}`, "
                f"cleanup `{result.get('cleanup_status', 'unknown')}`"
            )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
