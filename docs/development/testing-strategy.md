# Testing Strategy

## 1. Purpose

The project uses multiple testing levels to validate functionality, security, reliability, and RAG quality.

---

# 2. Testing Pyramid

```text
             E2E
              ▲
          Integration
              ▲
             Unit
              ▲
        Static Analysis
```

Most tests should be fast unit tests.

Critical cross-component behavior requires integration tests.

---

# 3. Unit Tests

Test individual components:

```text
PermissionService
JWT validation
Input validation
Chunking
Embedding adapters
Retrievers
Rerankers
Prompt builders
Citation validation
Security filters
```

---

# 4. Integration Tests

Test:

```text
FastAPI
   +
Supabase
   +
Qdrant Cloud
   +
Storage
```

Examples:

- Login → API request
- Upload → ingestion
- Document → Qdrant Cloud
- Query → authorized retrieval
- Query → generation
- Admin action → audit event

---

# 5. Authorization Tests

For every protected resource:

```text
Authorized user → ALLOW
Unauthorized user → DENY
Wrong department → DENY
Wrong classification → DENY
Revoked permission → DENY
Disabled user → DENY
```

---

# 6. RAG Security Tests

Critical tests include:

### Cross-department retrieval

```text
User A
  ↓
Query Department B
  ↓
No Department B chunks
```

### Revoked access

```text
User has access
  ↓
Permission revoked
  ↓
Query
  ↓
Document unavailable
```

### Prompt injection

```text
Malicious document
  ↓
Retrieved
  ↓
Model must treat it as data
```

### RAG poisoning

```text
Poisoned document
  ↓
Detection / quarantine
  ↓
Must not become trusted context
```

---

# 7. API Security Tests

Test:

- Missing JWT
- Expired JWT
- Invalid JWT
- Wrong audience
- Wrong issuer
- IDOR
- Privilege escalation
- Invalid input
- Oversized request
- Rate limiting
- Unauthorized admin calls

---

# 8. Frontend Tests

Test:

- Login
- Logout
- Session expiration
- Protected routes
- Permission-aware controls
- Chat
- Citations
- Documents
- Admin interface

---

# 9. End-to-End Tests

Example:

```text
Create user
   ↓
Assign role
   ↓
Upload document
   ↓
Ingest document
   ↓
Query document
   ↓
Retrieve authorized chunks
   ↓
Generate answer
   ↓
Validate citation
```

---

# 10. RAG Evaluation

Functional correctness is not enough.

Measure:

- Retrieval precision
- Retrieval recall
- Hit rate
- MRR
- NDCG
- Citation accuracy
- Answer faithfulness
- Answer relevance
- Abstention quality

---

# 11. Security Regression Tests

Every security bug should result in a regression test.

Example:

```text
Bug:
User could retrieve another department's chunk.

Fix:
Authorization filter corrected.

Regression:
CrossDepartmentRetrievalTest
```

---

# 12. Load Testing

Measure:

- API throughput
- Retrieval latency
- Reranking latency
- LLM latency
- Concurrent requests
- Memory usage
- CPU usage
- Qdrant Cloud performance

Use:

```text
P50
P90
P95
P99
```

---

# 13. Dependency Testing

Run:

- Python dependency scanning
- Node dependency scanning
- Container scanning
- Static analysis
- Secret scanning

---

# 14. CI Pipeline

Recommended:

```text
Commit
 ↓
Lint
 ↓
Type Check
 ↓
Unit Tests
 ↓
Security Tests
 ↓
Integration Tests
 ↓
Build
 ↓
Container Scan
```

---

# 15. Definition of Done

- [ ] Unit tests exist.
- [ ] Integration tests exist.
- [ ] Authorization tests exist.
- [ ] RAG security tests exist.
- [ ] API security tests exist.
- [ ] Frontend tests exist.
- [ ] E2E critical path exists.
- [ ] RAG evaluation dataset exists.
- [ ] CI runs automated tests.
- [ ] Security regressions become permanent tests.
