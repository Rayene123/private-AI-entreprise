# RAG Retrieval

## 1. Purpose

This document defines secure retrieval from Qdrant Cloud and other retrieval sources.

---

# 2. Retrieval Flow

```text
User
 ↓
Authenticated Identity
 ↓
Query Validation
 ↓
Permission Resolution
 ↓
Retrieval Filter
 ↓
Vector Search
 ↓
Keyword Search
 ↓
Merge
 ↓
Deduplicate
 ↓
Authorization Verification
 ↓
Rerank
 ↓
Context
```

---

# 3. Authorization Before Retrieval

The system must construct access filters before querying Qdrant Cloud.

Conceptually:

```text
user permissions
      ↓
allowed documents
      ↓
allowed departments
      ↓
allowed classifications
      ↓
Qdrant Cloud filter
```

Retrieving all documents and filtering afterward is less secure because restricted documents can influence retrieval results and potentially expose information through ranking behavior. OWASP recommends pre-retrieval filtering where possible.

---

# 4. Vector Retrieval

Vector retrieval uses:

```text
Query
 ↓
Embedding
 ↓
Qdrant Cloud similarity search
 ↓
Top K
```

The top-K value must be configurable.

---

# 5. Keyword Retrieval

Keyword retrieval helps with:

- Exact terms
- Names
- Numbers
- Codes
- Technical identifiers

---

# 6. Hybrid Retrieval

Results are combined:

```text
Vector results
+
Keyword results
 ↓
Normalization
 ↓
Deduplication
 ↓
Fusion
```

---

# 7. Reranking

The reranker evaluates candidate relevance.

Only authorized candidates may enter reranking.

---

# 8. Relevance Threshold

Results below a configurable relevance threshold may be discarded.

This reduces irrelevant context.

---

# 9. Retrieval Limits

Enforce:

```text
max_top_k
max_chunks
max_context_tokens
max_documents
```

These protect both performance and security.

---

# 10. Query Abuse

Monitor:

- High query frequency
- Repeated variations
- Systematic document probing
- Repeated restricted queries

Rate limiting should apply to retrieval endpoints.

---

# 11. Similarity Scores

Raw similarity scores should not normally be exposed to end users.

They can provide information about the underlying corpus.

---

# 12. Retrieval Logging

Record:

```text
user_id
query_id
retrieved_document_ids
retrieved_chunk_ids
timestamp
retrieval_method
```

Avoid storing full sensitive content unnecessarily.

---

# 13. Permission Changes

If permissions change:

```text
Permission revoked
      ↓
Next query
      ↓
New permission filter
      ↓
Restricted document excluded
```

Authorization must be evaluated at retrieval time.

---

# 14. Module 9 implementation

Module 9 currently implements semantic retrieval only through
`POST /chat/retrieve`:

```text
JWT
 ↓
chat.use + documents.read
 ↓
DocumentService active authorized IDs
 ↓
Ollama query embedding
 ↓
Qdrant filtered search
 ↓
DocumentService PostgreSQL revalidation per candidate
 ↓
Authorized chunks only
```

The configured Module 8 model, dimension, collection, and Qdrant client are
reused. Qdrant payload metadata is not authoritative. Missing or malformed
candidate metadata fails closed, while an unauthorized or stale document is
excluded. Empty authorized-document sets do not query Qdrant.

Configuration:

```text
RETRIEVAL_TOP_K=5
RETRIEVAL_MIN_SCORE=0.0
RETRIEVAL_MAX_QUERY_LENGTH=2000
```

Targeted verification:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m pytest -q tests\unit\test_retrieval_service.py tests\unit\test_qdrant_search.py tests\integration\test_chat_retrieval.py
```

Live verification passed with disposable Ollama, Qdrant Cloud, and Supabase
data on 2026-11-04:

```text
PASS: 8 live Module 9 checks
```

The verifier covered private owner access, department access, explicit share,
private and cross-department isolation, organization access, archived
exclusion, and cleanup.

Module 10 consumes this service directly and does not retrieve additional
documents during context assembly. Only authorized result objects can enter
the generation prompt.

# 15. Definition of Done

- [ ] Retrieval requires authentication.
- [ ] Permission filter is constructed first.
- [ ] Vector search exists.
- [ ] Keyword search exists.
- [ ] Hybrid fusion exists.
- [ ] Reranking exists.
- [ ] Retrieval limits exist.
- [ ] Query abuse controls exist.
- [ ] Retrieval is logged.
- [ ] Permission changes take effect without unsafe stale authorization.
