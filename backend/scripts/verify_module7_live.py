"""Disposable live verification for Module 7.

This script intentionally does not print credentials, tokens, storage paths, or
provider URLs. It creates only uniquely named temporary Supabase resources and
removes them in a finally block.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import sys
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.integrations.supabase.client import (
    SupabaseClientFactory,
    get_service_supabase_client,
    get_supabase_client,
)
from app.main import create_app
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.auth_service import AuthenticationService
from app.services.document_service import DocumentService
from app.services.permission_service import AuthorizationService

PDF_MIME = "application/pdf"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
TXT_MIME = "text/plain"
BUCKET = "enterprise-documents"
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def make_pdf() -> bytes:
    pages = [
        "Module 7 synthetic PDF page one",
        "Module 7 synthetic PDF page two",
    ]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        _pdf_stream(pages[0]),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Contents 7 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        _pdf_stream(pages[1]),
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def _pdf_stream(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 50 200 Td ({text}) Tj ET".encode()
    return f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"


def make_docx() -> bytes:
    from docx import Document
    from docx.shared import Inches

    document = Document()
    document.add_heading("Module 7 Synthetic DOCX", level=1)
    document.add_paragraph("This paragraph is synthetic and disposable.")
    table = document.add_table(rows=3, cols=2)
    values = [
        ("Role", "Access"),
        ("Employee", "Standard"),
        ("Manager", "Department"),
    ]
    for row, values_for_row in zip(table.rows, values):
        for cell, value in zip(row.cells, values_for_row):
            cell.text = value
    image_path = ROOT / "scripts" / ".module7-live-image.png"
    image_path.write_bytes(ONE_PIXEL_PNG)
    try:
        document.add_picture(str(image_path), width=Inches(0.1))
        output = BytesIO()
        document.save(output)
        return output.getvalue()
    finally:
        image_path.unlink(missing_ok=True)


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    settings = get_settings()
    service_client = get_service_supabase_client(settings)
    user_client = get_supabase_client(settings)
    _verify_service_connectivity(service_client)
    auth_admin = service_client.auth.admin
    prefix = f"module7-live-{secrets.token_hex(6)}"
    password = secrets.token_urlsafe(24)
    created_users: list[str] = []
    created_documents: list[str] = []
    created_objects: list[str] = []
    department_id: str | None = None
    explicit_grants: list[tuple[str, str]] = []
    checks: list[str] = []

    try:
        manager_id = _create_user(
            auth_admin,
            f"{prefix}-manager@example.invalid",
            password,
            created_users,
        )
        employee_id = _create_user(
            auth_admin,
            f"{prefix}-employee@example.invalid",
            password,
            created_users,
        )
        outsider_id = _create_user(
            auth_admin,
            f"{prefix}-outsider@example.invalid",
            password,
            created_users,
        )
        department_id = _create_department(service_client, prefix)
        _assign_department(service_client, manager_id, department_id)
        _assign_department(service_client, employee_id, department_id)
        _assign_role(service_client, manager_id, "manager")

        manager_token = _sign_in(user_client, f"{prefix}-manager@example.invalid", password)
        employee_token = _sign_in(user_client, f"{prefix}-employee@example.invalid", password)
        outsider_token = _sign_in(user_client, f"{prefix}-outsider@example.invalid", password)
        client = TestClient(create_app())

        manager_service = DocumentService(AuthorizationService(), supabase_client=service_client)
        employee_uuid = UUID(employee_id)
        manager_uuid = UUID(manager_id)

        txt_id = _create_and_upload(
            manager_service,
            manager_uuid,
            "Module 7 TXT",
            "txt.txt",
            TXT_MIME,
            "Résumé de contrôle\n\nDeuxième paragraphe synthétique.".encode(),
            created_documents,
            created_objects,
            access_level="private",
        )
        pdf_id = _create_and_upload(
            manager_service,
            manager_uuid,
            "Module 7 PDF",
            "document.pdf",
            PDF_MIME,
            make_pdf(),
            created_documents,
            created_objects,
            access_level="private",
        )
        docx_id = _create_and_upload(
            manager_service,
            manager_uuid,
            "Module 7 DOCX",
            "document.docx",
            DOCX_MIME,
            make_docx(),
            created_documents,
            created_objects,
            access_level="private",
        )
        shared_id = _create_and_upload(
            manager_service,
            manager_uuid,
            "Module 7 Shared",
            "shared.txt",
            TXT_MIME,
            b"Shared synthetic document.",
            created_documents,
            created_objects,
            access_level="private",
        )
        department_doc_id = _create_and_upload(
            manager_service,
            manager_uuid,
            "Module 7 Department",
            "department.txt",
            TXT_MIME,
            b"Department synthetic document.",
            created_documents,
            created_objects,
            access_level="department",
            department_id=department_id,
        )
        _grant_access(service_client, shared_id, employee_id)
        explicit_grants.append((shared_id, employee_id))
        _assert_direct_storage_denied(
            user_client,
            employee_token,
            created_objects[0],
        )
        checks.append("private-storage")

        for token, document_id, expected_text in (
            (manager_token, txt_id, "Résumé de contrôle"),
            (manager_token, pdf_id, "Module 7 synthetic PDF page one"),
            (manager_token, docx_id, "| Employee | Standard |"),
            (employee_token, shared_id, "Shared synthetic document."),
            (employee_token, department_doc_id, "Department synthetic document."),
        ):
            result = _ingest(client, token, document_id)
            assert result["document_id"] == document_id
            assert expected_text in result["markdown"]
            assert result["chunk_count"] == len(result["chunks"]) > 0
            assert [chunk["chunk_index"] for chunk in result["chunks"]] == list(
                range(result["chunk_count"])
            )
            assert all(chunk["text"] for chunk in result["chunks"])
            checks.append(f"ingest:{document_id}")

        pdf_result = _ingest(client, manager_token, pdf_id)
        assert "<!-- Page 1 -->" in pdf_result["markdown"]
        assert "<!-- Page 2 -->" in pdf_result["markdown"]
        docx_result = _ingest(client, manager_token, docx_id)
        assert "| Role | Access |" in docx_result["markdown"]
        assert "| Manager | Department |" in docx_result["markdown"]
        image_marker = ONE_PIXEL_PNG.hex()
        assert image_marker not in docx_result["markdown"]
        assert all(image_marker not in chunk["text"] for chunk in docx_result["chunks"])
        txt_result = _ingest(client, manager_token, txt_id)
        assert "Deuxième paragraphe synthétique." in txt_result["markdown"]
        expected_hash = hashlib.sha256(
            "Résumé de contrôle\n\nDeuxième paragraphe synthétique.".encode()
        ).hexdigest()
        assert txt_result["source_hash"] == expected_hash
        checks.append("content-metadata")

        for token, document_id, expected_status in (
            (outsider_token, txt_id, 403),
            (outsider_token, department_doc_id, 403),
        ):
            response = client.post(
                f"/documents/{document_id}/ingest",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == expected_status
            checks.append(f"denied:{document_id}")

        manager_service.update_document(
            manager_uuid,
            UUID(txt_id),
            DocumentUpdate(status="archived"),
        )
        archived_response = client.post(
            f"/documents/{txt_id}/ingest",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert archived_response.status_code == 404
        checks.append("archived-rejected")

        nonexistent = client.post(
            f"/documents/{uuid4()}/ingest",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert nonexistent.status_code == 404
        checks.append("nonexistent-rejected")

        print(f"PASS: {len(checks)} live Module 7 checks")
        return 0
    finally:
        _cleanup(
            service_client,
            auth_admin,
            created_documents,
            created_objects,
            explicit_grants,
            department_id,
            created_users,
        )


def _create_user(auth_admin, email: str, password: str, created_users: list[str]) -> str:
    response = auth_admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user = getattr(response, "user", None)
    user_id = str(getattr(user, "id", ""))
    if not user_id:
        raise RuntimeError("Supabase Auth did not return a temporary user ID.")
    created_users.append(user_id)
    return user_id


def _verify_service_connectivity(service_client) -> None:
    try:
        response = service_client.table("roles").select("name").limit(1).execute()
        rows = response.data if hasattr(response, "data") else response.get("data")
        if not isinstance(rows, list):
            raise RuntimeError("Supabase returned an invalid roles response.")
    except Exception as exc:
        raise RuntimeError(
            "Supabase service-role connectivity or schema access failed."
        ) from exc


def _sign_in(client, email: str, password: str) -> str:
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    session = getattr(response, "session", None)
    token = getattr(session, "access_token", None)
    if not token:
        raise RuntimeError("Supabase Auth did not return a temporary access token.")
    return token


def _assert_direct_storage_denied(client, token: str, storage_path: str) -> None:
    try:
        client.storage.set_auth(token)
        client.storage.from_(BUCKET).download(storage_path)
    except Exception:
        return
    raise RuntimeError("A non-service authenticated client accessed private Storage.")


def _create_department(client, prefix: str) -> str:
    response = client.table("departments").insert({"name": prefix}).execute()
    rows = response.data if hasattr(response, "data") else response.get("data")
    if not rows:
        raise RuntimeError("Could not create the temporary department.")
    return str(rows[0]["id"])


def _assign_department(client, user_id: str, department_id: str) -> None:
    client.table("profiles").update({"department_id": department_id}).eq(
        "id", user_id
    ).execute()


def _assign_role(client, user_id: str, role_name: str) -> None:
    role_response = client.table("roles").select("id").eq("name", role_name).single().execute()
    role_id = role_response.data["id"]
    client.table("user_roles").insert({"user_id": user_id, "role_id": role_id}).execute()


def _create_and_upload(
    service: DocumentService,
    owner_id: UUID,
    title: str,
    filename: str,
    mime_type: str,
    content: bytes,
    created_documents: list[str],
    created_objects: list[str],
    *,
    access_level: str,
    department_id: str | None = None,
) -> str:
    document = service.create_document(
        owner_id,
        DocumentCreate(
            title=title,
            access_level=access_level,
            department_id=UUID(department_id) if department_id else None,
        ),
    )
    document_id = str(document.id)
    created_documents.append(document_id)
    uploaded = service.upload_document_file(
        owner_id,
        document.id,
        filename=filename,
        content_type=mime_type,
        content=content,
    )
    if not uploaded.storage_path:
        raise RuntimeError("Upload did not return a server-generated storage path.")
    created_objects.append(uploaded.storage_path)
    return document_id


def _grant_access(client, document_id: str, user_id: str) -> None:
    client.table("document_user_access").insert(
        {"document_id": document_id, "user_id": user_id}
    ).execute()


def _ingest(client: TestClient, token: str, document_id: str) -> dict:
    response = client.post(
        f"/documents/{document_id}/ingest",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Live ingestion failed with HTTP {response.status_code}.")
    return response.json()


def _cleanup(
    service_client,
    auth_admin,
    document_ids: list[str],
    object_paths: list[str],
    explicit_grants: list[tuple[str, str]],
    department_id: str | None,
    user_ids: list[str],
) -> None:
    for document_id, user_id in explicit_grants:
        service_client.table("document_user_access").delete().eq(
            "document_id", document_id
        ).eq("user_id", user_id).execute()
    bucket = service_client.storage.from_(BUCKET)
    for path in object_paths:
        bucket.remove([path])
    for document_id in document_ids:
        service_client.table("documents").delete().eq("id", document_id).execute()
    if department_id:
        service_client.table("departments").delete().eq("id", department_id).execute()
    for user_id in user_ids:
        auth_admin.delete_user(user_id)


if __name__ == "__main__":
    raise SystemExit(main())
