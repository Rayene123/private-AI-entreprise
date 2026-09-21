# RAG Architecture

## 1. Purpose

This document defines the architecture of the Retrieval-Augmented Generation system.

The RAG system must provide:

- Permission-aware retrieval
- Hybrid search
- Semantic retrieval
- Keyword retrieval
- Reranking
- Citation generation
- Source attribution
- Secure context construction
- Controlled generation
- Graceful abstention

---

# 2. Architecture

```text
User Query
    ↓
Query Validation
    ↓
Query Analysis
    ↓
Identity + Permissions
    ↓
Retrieval Filter
    ↓
┌────────────────────────────┐
│ Hybrid Retrieval           │
│                            │
│ Vector Search              │
│ Keyword Search             │
└─────────────┬──────────────┘
              ↓
Candidate Chunks
              ↓
Permission Verification
              ↓
Reranking
              ↓
Context Construction
              ↓
Prompt Injection Checks
              ↓
Ollama
              ↓
Output Validation
              ↓
Citation Validation
              ↓
Response
```

---

# 3. RAG Components

```text
rag/
├── ingestion/
├── embeddings/
├── retrieval/
├── authorization/
├── generation/
├── pipelines/
└── types.py
```

Each component must have a clear responsibility.

---

# 4. Ingestion

Ingestion converts source documents into searchable chunks.

```text
Document
 ↓
Validation
 ↓
Parsing
 ↓
Cleaning
 ↓
Chunking
 ↓
Metadata enrichment
 ↓
Embedding
 ↓
Qdrant Cloud
```

The original document remains in Supabase Storage.

PostgreSQL stores authoritative metadata.

---

# 5. Chunk Metadata

Every chunk must carry sufficient metadata for authorization.

Example:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "department_id": "...",
  "classification": "CONFIDENTIAL",
  "owner_id": "...",
  "allowed_roles": [],
  "allowed_users": [],
  "embedding_model": "...",
  "document_hash": "..."
}
```

Access-control metadata must survive chunking and embedding. OWASP specifically recommends carrying access-control metadata to vector chunks and enforcing access control during retrieval.

---

# 6. Retrieval

Retrieval consists of:

1. Query normalization
2. Permission filter construction
3. Vector search
4. Keyword search
5. Candidate merging
6. Deduplication
7. Authorization verification
8. Reranking

---

# 7. Permission-Aware Retrieval

The system must construct the retrieval filter from the authenticated user's permissions.

Conceptually:

```text
User
 ↓
Effective Permissions
 ↓
Allowed Departments
 ↓
Allowed Classifications
 ↓
Allowed Documents
 ↓
Qdrant Cloud Filter
```

Unauthorized chunks should be excluded before they reach the model.

---

# 8. Hybrid Retrieval

Hybrid retrieval combines:

```text
Semantic Search
+
Keyword Search
```

Semantic search handles conceptual similarity.

Keyword search improves retrieval for:

- Names
- IDs
- Technical terms
- Legal terminology
- Exact phrases
- Product codes

The two result sets are merged before reranking.

---

# 9. Reranking

The reranker receives candidate chunks and produces an improved relevance ordering.

Example:

```text
Vector candidates
+
Keyword candidates
        ↓
   Deduplication
        ↓
      Reranker
        ↓
Top N
```

Reranking must occur only after authorization boundaries have been respected.

---

# 10. Context Construction

Context should contain:

```text
Document metadata
Chunk content
Source reference
Classification
Provenance
```

Retrieved content must be clearly delimited from system instructions.

Example:

```text
BEGIN RETRIEVED CONTENT

[document content]

END RETRIEVED CONTENT
```

Retrieved content is data, not instructions. OWASP recommends explicit delimiters and limits on retrieved content to reduce context-window attacks.

---

# 11. Context Limits

The system should limit:

- Number of chunks
- Total tokens
- Maximum chunk size
- Maximum documents per request

This prevents context flooding and improves relevance.

Initial configurable defaults can be established during implementation and evaluated experimentally.

---

# 12. Citation Architecture

Every generated factual answer should be traceable to retrieved sources where applicable.

A citation should contain:

```text
document_id
chunk_id
document_name
page/section where available
```

The frontend should render citations as clickable source references where appropriate.

---

# 13. Citation Validation

Before returning citations:

```text
Generated citation
      ↓
Does source exist?
      ↓
Is source authorized?
      ↓
Does source belong to retrieved context?
      ↓
Valid citation
```

Invalid citations should not be exposed.

---

# 14. Abstention

The RAG system should be able to say that available evidence is insufficient.

Examples:

```text
No authorized sources found.
```

or:

```text
I could not find sufficient information in the available documents.
```

The model should not invent evidence when retrieval is insufficient.

---

# 15. Failure Behavior

Security-sensitive RAG failures should fail closed.

Examples:

```text
Authorization unavailable → no retrieval
Qdrant Cloud unavailable → no fabricated RAG answer
Citation validation fails → block invalid citation
Document integrity fails → exclude document
```

OWASP's RAG guidance explicitly recommends fail-closed behavior for retrieval and authorization failures.

---

# 16. Definition of Done

- [ ] Ingestion produces metadata-rich chunks.
- [ ] Permissions propagate to chunks.
- [ ] Retrieval is permission-aware.
- [ ] Vector search exists.
- [ ] Keyword search exists.
- [ ] Hybrid retrieval exists.
- [ ] Reranking exists.
- [ ] Context is delimited.
- [ ] Context size is controlled.
- [ ] Citations are generated.
- [ ] Citations are validated.
- [ ] Abstention is supported.
- [ ] Retrieval failures fail securely.
