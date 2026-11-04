from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

from app.core.exceptions import ValidationError

PDF_MIME = "application/pdf"
TXT_MIME = "text/plain"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass(frozen=True)
class ContentBlock:
    kind: str
    content: str | tuple[tuple[str, ...], ...]
    page_number: int | None = None


def parse_document(content: bytes, mime_type: str) -> list[ContentBlock]:
    if mime_type == TXT_MIME:
        return _parse_txt(content)
    if mime_type == DOCX_MIME:
        return _parse_docx(content)
    if mime_type == PDF_MIME:
        return _parse_pdf(content)
    raise ValidationError(
        "The document format is not supported for ingestion.",
        code="unsupported_document_type",
    )


def _parse_txt(content: bytes) -> list[ContentBlock]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            "The text document is not valid UTF-8.",
            code="text_decoding_failed",
        ) from exc
    return [ContentBlock("paragraph", text.replace("\r\n", "\n").replace("\r", "\n"))]


def _parse_docx(content: bytes) -> list[ContentBlock]:
    try:
        from docx import Document
        from docx.document import Document as DocumentType
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError as exc:
        raise ValidationError(
            "DOCX parsing is not available.",
            code="docx_parser_unavailable",
        ) from exc

    try:
        document: DocumentType = Document(BytesIO(content))
        blocks: list[ContentBlock] = []
        for item in _iter_docx_block_items(document):
            if isinstance(item, Paragraph):
                text = item.text.strip()
                if not text:
                    continue
                style = (item.style.name or "").lower() if item.style else ""
                if style.startswith("heading"):
                    level = style.split()[-1]
                    level = int(level) if level.isdigit() else 1
                    blocks.append(ContentBlock("heading", f"{'#' * level} {text}"))
                elif "list" in style:
                    blocks.append(ContentBlock("list", f"- {text}"))
                else:
                    blocks.append(ContentBlock("paragraph", text))
            elif isinstance(item, Table):
                rows = tuple(
                    tuple(cell.text.strip().replace("\n", " ") for cell in row.cells)
                    for row in item.rows
                )
                if rows:
                    blocks.append(ContentBlock("table", rows))
        return blocks
    except Exception as exc:
        raise ValidationError(
            "The DOCX document could not be parsed.",
            code="invalid_docx",
        ) from exc


def _iter_docx_block_items(document: object) -> Iterable[object]:
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    parent = document.element.body
    for child in parent.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def _parse_pdf(content: bytes) -> list[ContentBlock]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValidationError(
            "PDF parsing is not available.",
            code="pdf_parser_unavailable",
        ) from exc

    try:
        reader = PdfReader(BytesIO(content))
        blocks: list[ContentBlock] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n")
            if text.strip():
                blocks.append(ContentBlock("paragraph", text, page_number))
            blocks.extend(_extract_pdf_tables(content, page_number))
        if not blocks:
            raise ValidationError(
                "The PDF contains no extractable text.",
                code="no_extractable_content",
            )
        return blocks
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(
            "The PDF document could not be parsed.",
            code="invalid_pdf",
        ) from exc


def _extract_pdf_tables(content: bytes, page_number: int) -> list[ContentBlock]:
    try:
        import pdfplumber
    except ImportError:
        return []
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            page = pdf.pages[page_number - 1]
            blocks = []
            for table in page.extract_tables() or []:
                rows = tuple(
                    tuple((cell or "").strip().replace("\n", " ") for cell in row)
                    for row in table
                    if any(cell and cell.strip() for cell in row)
                )
                if rows:
                    blocks.append(ContentBlock("table", rows, page_number))
            return blocks
    except Exception:
        return []
