# RAG Ingestion

## 1. Purpose

The ingestion pipeline converts enterprise documents into secure searchable representations.

---

# 2. Pipeline

```text
Upload
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
Embedding
 ↓
Qdrant Cloud
 ↓
Index Validation
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

# 6. Parsing

Parsers should extract:

- Text
- Pages
- Headings
- Tables where supported
- Metadata

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

Chunks should preserve:

- Document ID
- Page
- Section
- Heading
- Position
- Permissions
- Classification

Chunking must not separate content from its authorization metadata.

---

# 10. Embedding

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

# 14. Definition of Done

- [ ] Upload validation exists.
- [ ] SHA-256 hashing exists.
- [ ] Provenance is stored.
- [ ] Private storage is used.
- [ ] Parsing is modular.
- [ ] Cleaning is modular.
- [ ] Security scanning exists.
- [ ] Chunk metadata is preserved.
- [ ] Permissions propagate to chunks.
- [ ] Embedding version is stored.
- [ ] Qdrant Cloud indexing is controlled.
- [ ] Deletion propagates.
- [ ] Reprocessing is supported.
