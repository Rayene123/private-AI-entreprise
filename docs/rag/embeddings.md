# Embeddings

Module 8 uses the Ollama `/api/embed` endpoint through a provider interface.
The default model is `nomic-embed-text`; model, URL, batch size, timeout, and
dimension are configuration-driven. Empty input, malformed vectors, non-finite
values, incomplete batches, and dimension mismatches are rejected before
indexing.

## 1. Purpose

This document defines how text embeddings are generated, versioned, stored, and managed.

---

# 2. Embedding Pipeline

```text
Chunk
 ↓
Normalization
 ↓
Embedding Model
 ↓
Vector
 ↓
Metadata
 ↓
Qdrant Cloud
```

---

# 3. Embedding Model

The embedding implementation must be abstracted.

Example:

```python
class EmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
```

This allows the model to be replaced without rewriting retrieval logic.

---

# 4. Model Versioning

Every indexed chunk should record:

```text
embedding_model
embedding_version
embedding_dimension
```

---

# 5. Consistency

All vectors within a Qdrant Cloud collection must use compatible dimensions and distance configuration.

Changing the embedding model may require rebuilding the collection.

---

# 6. Security

Embeddings are sensitive.

They must inherit the access-control requirements of the source document.

They must not be publicly exposed.

OWASP warns that embeddings should not automatically be treated as irreversible or harmless representations of the source content.

---

# 7. Access Control

Each embedding payload must contain enough metadata to construct authorization filters.

Example:

```json
{
  "document_id": "...",
  "department_id": "...",
  "classification": "...",
  "allowed_roles": []
}
```

---

# 8. Batch Processing

Embedding generation should support batches.

Benefits:

- Better throughput
- Reduced overhead
- Controlled resource usage

Batch size must be configurable.

---

# 9. Failure Handling

If embedding generation fails:

```text
Do not index incomplete chunk
```

The document should remain in a processing state until the pipeline completes successfully.

---

# 10. Re-Embedding

Re-embedding should support:

```text
Old model
 ↓
New model
 ↓
New index
 ↓
Validation
 ↓
Switch
```

Avoid destroying the only valid index before the replacement is ready.

---

# 11. Monitoring

Monitor:

- Embedding latency
- Batch size
- Failure rate
- Vector dimensions
- Model version
- Distribution changes

---

# 12. Definition of Done

- [x] Embedding interface exists.
- [x] Model and dimensions are configuration-driven and recorded.
- [x] Vector dimensions and finite values are validated.
- [x] Authorization metadata is stored in Qdrant payloads.
- [x] Embeddings remain backend-only.
- [x] Batch processing and safe provider failure handling exist.
- [x] Re-indexing uses deterministic IDs and removes obsolete source versions.
- [x] Live Ollama generation and Qdrant indexing verified with disposable data.
- [ ] Retrieval, monitoring, and model migration orchestration belong to later work.
