# RAG Ingestion

Module 7 implements the secure pre-RAG ingestion pipeline. The original
uploaded document remains authoritative; canonical Markdown is a derived
in-memory representation used for ingestion and chunking.

## 1. Purpose

The ingestion pipeline converts enterprise documents into secure searchable representations.

---

# 2. Pipeline

```text
Authentication and authorization
 ↓
Authorized private Storage download
 ↓
File Validation
 ↓
Integrity Hash
 ↓
Storage
 ↓
Metadata
 ↓
Parsing
 ↓
Cleaning
 ↓
Security Inspection
 ↓
Chunking
 ↓
Metadata Propagation
 ↓
Structured ingestion result
```

---

# 3. File Validation

Validate:

- File type
- MIME type
- File size
- Filename
- Extension
- Content structure

Never trust the extension alone.

---

# 4. Integrity

Generate a SHA-256 hash for each document.

Store:

```text
document_hash
```

This allows later integrity verification.

OWASP's current RAG guidance recommends hashing documents and tracking provenance during ingestion.

---

# 5. Storage

The original document is stored in a private Supabase Storage bucket.

PostgreSQL stores:

```text
document_id
storage_path
owner_id
department_id
classification
document_hash
status
```

---

# 6. Parsing and canonical Markdown

Parsers should extract:

- Text
- Pages
- Headings
- Tables where supported
- Page context for PDFs where available

PDF, DOCX, and UTF-8 TXT all converge to deterministic canonical Markdown
before chunking. DOCX tables are extracted directly. PDF tables are extracted
when `pdfplumber` can reliably identify them; their text is never silently
discarded. Embedded images are intentionally not OCR'd, captioned, embedded,
or sent to an LLM. Scanned PDFs without extractable text return a safe error.

Parsing should be isolated from chunking.

---

# 7. Cleaning

Cleaning may include:

- Whitespace normalization
- Duplicate whitespace removal
- Invalid character handling
- Metadata normalization
- Unicode normalization

Cleaning must not remove information needed for security or provenance.

---

# 8. Security Inspection

Inspect for:

- Prompt injection
- Hidden instructions
- Suspicious Unicode
- Unexpected embedded content
- Malformed structures

Potential states:

```text
UNVERIFIED
TRUSTED
QUARANTINED
REJECTED
```

---

# 9. Chunking

The configurable character approximation targets 1000-1500 tokens with
100-200 token overlap. Chunk IDs are deterministic hashes of
`document_id + source_hash + chunk_index`.

Chunks preserve:

- Document ID
- Page
- Section
- Heading
- Position
- Permissions
- Classification

Chunking must not separate content from its authorization metadata.

---

# 10. Future embedding

Each chunk is converted into an embedding.

Store the embedding model version.

Example:

```text
embedding_model
embedding_dimension
embedding_version
```

This makes future re-indexing reproducible.

---

# 11. Qdrant Cloud Indexing

Only validated chunks should be inserted.

Qdrant Cloud payload must include authorization metadata.

Application users should not have direct write access to the vector index.

---

# 12. Deletion

Deleting a document must propagate:

```text
Storage
 ↓
PostgreSQL
 ↓
Qdrant Cloud
```

No orphaned chunks should remain searchable.

OWASP recommends cascading deletion of derived vectors and cached data when source documents are deleted or de-permissioned.

---

# 13. Reprocessing

Documents may be reprocessed when:

- Parser changes
- Chunking changes
- Embedding model changes
- Security scanning changes
- Metadata changes

Reprocessing should create a controlled indexing operation rather than silently modifying the existing index.

---

# 14. Module 7 Definition of Done

- [x] Upload validation exists in Module 6.
- [x] SHA-256 hashing exists for downloaded bytes.
- [x] Private storage is reused.
- [x] Parsing, normalization, Markdown conversion, and chunking are modular.
- [x] Authorization is enforced before Storage download.
- [x] Chunk metadata and source provenance are returned.
- [ ] OCR, embeddings, Qdrant indexing, deletion propagation, and reprocessing belong to later modules.

## 15. Verification

The local FastAPI endpoint integration suite covers authorized and denied
document access, department/private/explicit-share authorization outcomes,
archived and missing documents, missing Storage objects, unsupported MIME
types, PDF/DOCX/TXT ingestion, table preservation, structured responses, and
the authorization-before-download invariant. The full backend suite passed
with 135 tests and 2 warnings.

Live Supabase verification passed using disposable Auth users and synthetic
PDF, DOCX, and TXT fixtures. The verifier confirmed authorized ingestion,
department access, explicit sharing, denied private/department access, archived
document rejection, nonexistent-document rejection, private Storage denial for
non-service access, table/page/text preservation, source hashing, and chunk
metadata. Cleanup removed all temporary users, metadata, grants, and Storage
objects.
# Controlled public-reference dataset ingestion

The corporate reference inventory is ingested only by
`backend/scripts/ingest_corporate_dataset.py`. The runner validates the six
local PDFs, resolves existing HR, IT, and Finance departments, and requires an
explicit existing owner account through `DATASET_INGESTION_OWNER_ID`.

The runner creates documents through `DocumentService`, uploads through the
private Storage boundary, and indexes through `DocumentIndexingService`. It
does not insert document rows directly or write to Qdrant directly. Each
document stores its dataset ID, source organization, source URL, dates,
document type, and source SHA-256 in `documents.source_metadata`. The nullable
column and dataset-ID index are defined in
`backend/app/db/migrations/004_module11_dataset_provenance.sql`.

The runner is idempotent for an identical source hash. A repeated run skips a
document already marked `indexed`; a changed hash for an existing dataset ID
fails safely and requires manual review. It never automatically deletes or
archives existing documents.

Before processing any document, it validates the complete inventory, including
exact filenames, file sizes, SHA-256 readability, HTTPS provenance URLs,
organizations, departments, access levels, source type, and supplied dates.
It also preflights the selected owner's active profile and
`documents.create`, `documents.update`, and `documents.read` permissions.

If a newly created document fails after creation, the runner removes its
created index points when indexing has started, removes its Storage object,
and archives the newly created document. Existing documents are never cleaned
up by this path. Reports contain only a processing stage, safe error code, and
cleanup status; detailed exceptions remain in structured application logs.
