from uuid import uuid4
from io import BytesIO

import pytest

from app.core.exceptions import AuthorizationError, ValidationError
from app.rag.ingestion.chunking import MarkdownChunker, sha256_bytes
from app.rag.ingestion.markdown import blocks_to_markdown
from app.rag.ingestion.parsers import ContentBlock, parse_document
from app.schemas.document import DocumentFile
from app.services.document_ingestion_service import DocumentIngestionService


def test_txt_parsing_and_markdown_are_deterministic() -> None:
    blocks = parse_document(b"Title\r\n\r\nA  paragraph.", "text/plain")
    markdown = blocks_to_markdown(blocks)
    assert markdown == "Title\n\nA paragraph."
    assert markdown == blocks_to_markdown(parse_document(b"Title\r\n\r\nA  paragraph.", "text/plain"))


def test_tables_are_valid_markdown_and_preserve_values() -> None:
    markdown = blocks_to_markdown(
        [
            ContentBlock("heading", "# Employees"),
            ContentBlock("table", (("Employee", "Role"), ("John", "Manager"))),
        ]
    )
    assert "| Employee | Role |" in markdown
    assert "|---|---|" in markdown
    assert "| John | Manager |" in markdown


def test_pdf_page_context_is_preserved() -> None:
    markdown = blocks_to_markdown(
        [ContentBlock("paragraph", "One", 1), ContentBlock("paragraph", "Two", 2)]
    )
    assert "<!-- Page 1 -->" in markdown
    assert "<!-- Page 2 -->" in markdown


def test_chunking_hash_and_identity_are_deterministic() -> None:
    document_id = uuid4()
    content = "# Heading\n\n" + ("word " * 500)
    source_hash = sha256_bytes(content.encode())
    first = MarkdownChunker(100, 10).chunk(document_id, content, source_hash)
    second = MarkdownChunker(100, 10).chunk(document_id, content, source_hash)
    assert len(first) > 1
    assert first == second
    assert all(chunk.text for chunk in first)
    assert all(chunk.chunk_id for chunk in first)


def test_invalid_chunk_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        MarkdownChunker(10, 10)
    assert error.value.code == "invalid_chunk_configuration"


def test_invalid_utf8_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        parse_document(b"\xff", "text/plain")
    assert error.value.code == "text_decoding_failed"


def test_docx_parsing_preserves_heading_paragraph_and_table() -> None:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("Policy", level=1)
    document.add_paragraph("Employees must follow the policy.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Role"
    table.cell(0, 1).text = "Access"
    table.cell(1, 0).text = "Employee"
    table.cell(1, 1).text = "Standard"
    buffer = BytesIO()
    document.save(buffer)

    markdown = blocks_to_markdown(
        parse_document(
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    )
    assert "# Policy" in markdown
    assert "Employees must follow the policy." in markdown
    assert "| Employee | Standard |" in markdown


def test_unauthorized_ingestion_does_not_download() -> None:
    class ForbiddenDocuments:
        def __init__(self) -> None:
            self.download_called = False

        def download_document_file(self, user_id, document_id):
            self.download_called = True
            raise AssertionError("download must not be called")

    documents = ForbiddenDocuments()
    service = DocumentIngestionService(documents)  # type: ignore[arg-type]
    documents.download_document_file = lambda user_id, document_id: (
        (_ for _ in ()).throw(
            AuthorizationError("denied", code="document_access_denied")
        )
    )
    with pytest.raises(AuthorizationError):
        service.ingest(uuid4(), uuid4())
    assert documents.download_called is False
