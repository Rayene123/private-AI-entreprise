from uuid import UUID

from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.core.config import get_settings
from app.rag.ingestion.chunking import MarkdownChunker, sha256_bytes
from app.rag.ingestion.markdown import blocks_to_markdown
from app.rag.ingestion.parsers import parse_document
from app.schemas.ingestion import IngestionChunk, IngestionResponse
from app.services.document_service import DocumentService
from app.services.document_file_policy import validate_upload


class DocumentIngestionService:
    def __init__(
        self,
        document_service: DocumentService,
        chunker: MarkdownChunker | None = None,
    ) -> None:
        self._documents = document_service
        self._chunker = chunker or MarkdownChunker()

    def ingest(self, user_id: UUID, document_id: UUID) -> IngestionResponse:
        # DocumentService performs authentication-independent RBAC, profile,
        # active-document, and document-level checks before downloading.
        document_file = self._documents.download_document_file(user_id, document_id)
        if not document_file.content:
            raise ResourceNotFoundError(
                "The document file was not found.",
                code="document_file_not_found",
            )
        validate_upload(
            filename=document_file.filename,
            content_type=document_file.mime_type,
            content=document_file.content,
            settings=get_settings(),
        )
        source_hash = sha256_bytes(document_file.content)
        try:
            blocks = parse_document(document_file.content, document_file.mime_type)
            markdown = blocks_to_markdown(blocks)
            chunks = self._chunker.chunk(UUID(str(document_id)), markdown, source_hash)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(
                "The document could not be ingested.",
                code="ingestion_failed",
            ) from exc
        return IngestionResponse(
            document_id=document_id,
            source_hash=source_hash,
            file_type=document_file.mime_type,
            markdown_length=len(markdown),
            chunk_count=len(chunks),
            markdown=markdown,
            chunks=[
                IngestionChunk(
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    source_hash=chunk.source_hash,
                    page_number=chunk.page_number,
                    chunk_id=chunk.chunk_id,
                )
                for chunk in chunks
            ],
        )
