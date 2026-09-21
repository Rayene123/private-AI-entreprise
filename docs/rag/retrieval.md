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

# 14. Definition of Done

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
