# Markdown Chunking

Module 7 chunks the canonical Markdown representation, never raw PDF, DOCX,
or TXT parser output. The default configuration uses a deterministic
character approximation of 1200 tokens with 150-token overlap. Configuration
rejects non-positive chunk sizes and overlap greater than or equal to the
chunk size.

Chunks preserve document order, Markdown headings, page markers, tables, and
the following metadata:

- `document_id`
- `chunk_index`
- `text`
- `source_hash`
- `page_number` when a PDF page marker is present
- deterministic `chunk_id`

The chunk ID is derived from `document_id`, `source_hash`, and
`chunk_index`; it is not random. Source bytes are hashed with SHA-256 before
parsing. The original uploaded document remains authoritative, and Module 7
does not persist chunks or embeddings. Vector indexing is deferred to a later
module.

Live verification confirmed sequential chunk indices, non-empty chunk text,
deterministic source hashing, and deterministic chunk IDs for synthetic PDF,
DOCX, and TXT documents.
