from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import ValidationError


@dataclass(frozen=True)
class Chunk:
    document_id: UUID
    chunk_index: int
    text: str
    source_hash: str
    page_number: int | None = None
    chunk_id: str = ""


class MarkdownChunker:
    def __init__(self, chunk_size_tokens: int = 1200, overlap_tokens: int = 150) -> None:
        if chunk_size_tokens <= 0 or overlap_tokens < 0 or overlap_tokens >= chunk_size_tokens:
            raise ValidationError(
                "Chunk size and overlap configuration is invalid.",
                code="invalid_chunk_configuration",
            )
        self.chunk_size = chunk_size_tokens * 4
        self.overlap = overlap_tokens * 4

    def chunk(self, document_id: UUID, markdown: str, source_hash: str) -> list[Chunk]:
        text = markdown.strip()
        if not text:
            raise ValidationError(
                "The document contains no extractable content.",
                code="no_extractable_content",
            )
        pieces = self._split(text)
        chunks: list[Chunk] = []
        for index, piece in enumerate(pieces):
            page_match = re.search(r"<!-- Page (\d+) -->", piece)
            page = int(page_match.group(1)) if page_match else None
            chunk_id = hashlib.sha256(
                f"{document_id}:{source_hash}:{index}".encode()
            ).hexdigest()
            chunks.append(
                Chunk(
                    document_id=document_id,
                    chunk_index=index,
                    text=piece,
                    source_hash=source_hash,
                    page_number=page,
                    chunk_id=chunk_id,
                )
            )
        return chunks

    def _split(self, text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(paragraph) <= self.chunk_size:
                current = paragraph
            else:
                chunks.extend(
                    paragraph[start : start + self.chunk_size]
                    for start in range(0, len(paragraph), self.chunk_size - self.overlap)
                )
                current = ""
        if current:
            chunks.append(current)
        if self.overlap and len(chunks) > 1:
            chunks = [
                (chunks[i - 1][-self.overlap :] + "\n\n" + chunk).strip()
                if i > 0 else chunk
                for i, chunk in enumerate(chunks)
            ]
        return chunks


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
