"""Server-authoritative file validation and storage path generation.

The backend never trusts a client-supplied filename or storage path. This
module sanitizes filenames, validates uploaded files against configured
limits, and deterministically derives the storage object path from the
document ID, which itself only ever comes from an authorized document
record loaded server-side.
"""

import re
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.exceptions import ValidationError

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_FILENAME_LENGTH = 150

# Minimal magic-byte signatures for the currently supported document types.
# `text/plain` has no reliable binary signature, so it is validated by MIME
# type and content decodability only; this is documented as the current
# validation boundary, not full content inspection.
_MIME_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ): (b"PK\x03\x04",),
}


class ValidatedFile:
    """A file that has passed server-side validation."""

    __slots__ = ("content", "mime_type", "original_filename", "size_bytes")

    def __init__(self, content: bytes, mime_type: str, original_filename: str) -> None:
        self.content = content
        self.mime_type = mime_type
        self.original_filename = original_filename
        self.size_bytes = len(content)


def validate_upload(
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    settings: Settings,
) -> ValidatedFile:
    """Validate an uploaded file against configured, centralized limits."""

    if not content:
        raise ValidationError(
            "The uploaded file is empty.",
            code="empty_file",
        )

    if len(content) > settings.max_document_file_size:
        raise ValidationError(
            "The uploaded file exceeds the maximum allowed size.",
            code="file_too_large",
        )

    mime_type = (content_type or "").split(";")[0].strip().lower()
    if mime_type not in settings.allowed_document_mime_types:
        raise ValidationError(
            "The uploaded file type is not supported.",
            code="unsupported_mime_type",
        )

    safe_filename = sanitize_filename(filename)

    signatures = _MIME_SIGNATURES.get(mime_type)
    if signatures and not any(content.startswith(sig) for sig in signatures):
        raise ValidationError(
            "The uploaded file content signature does not match its declared type.",
            code="file_signature_mismatch",
        )

    return ValidatedFile(
        content=content,
        mime_type=mime_type,
        original_filename=safe_filename,
    )


def sanitize_filename(filename: str | None) -> str:
    """Reduce a client-supplied filename to a safe display name only.

    The sanitized value is used for the stored ``original_filename`` display
    field. It is never used to construct a storage path.
    """

    if not filename or not filename.strip():
        raise ValidationError(
            "The filename is not allowed.",
            code="unsafe_filename",
        )

    normalized = filename.strip()
    if any(sep in normalized for sep in ("/", "\\")):
        raise ValidationError(
            "The filename is not allowed.",
            code="unsafe_filename",
        )

    if "\x00" in normalized or normalized in (".", "..") or normalized.startswith("."):
        raise ValidationError(
            "The filename is not allowed.",
            code="unsafe_filename",
        )

    sanitized = _SAFE_FILENAME_PATTERN.sub("_", normalized).strip("._")
    if not sanitized:
        raise ValidationError(
            "The filename is not allowed.",
            code="unsafe_filename",
        )

    return sanitized[:_MAX_FILENAME_LENGTH]


def generate_storage_path(document_id: UUID, original_filename: str) -> str:
    """Deterministically derive the storage object path server-side.

    The document ID must come from an authorized document record, never
    from client input. The generated filename component is random and
    unrelated to any client-supplied path, which prevents path traversal
    and collisions between replacement uploads.
    """

    extension = PurePosixPath(original_filename).suffix
    extension = _SAFE_FILENAME_PATTERN.sub("", extension)[:20]
    generated_filename = f"{uuid4().hex}{extension}"
    return f"documents/{document_id}/{generated_filename}"