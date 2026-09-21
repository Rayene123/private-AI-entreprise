# RAG Evaluation

## 1. Purpose

This document defines the evaluation strategy for the RAG system.

The evaluation must measure both:

- Retrieval quality
- Generation quality

and separately:

- Security correctness

---

# 2. Evaluation Dataset

Create a controlled dataset containing:

```text
Question
Expected documents
Expected chunks
Expected answer
Expected citations
Authorization context
```

Example:

```json
{
  "question": "What is the vacation policy?",
  "expected_documents": ["hr_policy.pdf"],
  "authorized_roles": ["employee"]
}
```

---

# 3. Retrieval Metrics

Measure:

### Precision@K

How many retrieved documents are relevant?

### Recall@K

How many relevant documents were retrieved?

### MRR

Measures the rank of the first relevant result.

### NDCG

Measures ranking quality across multiple relevant results.

---

# 4. Generation Metrics

Measure:

- Answer relevance
- Faithfulness
- Citation correctness
- Citation completeness
- Context utilization
- Abstention correctness

---

# 5. Security Metrics

Security evaluation is equally important.

Measure:

```text
Unauthorized retrieval rate
Prompt injection success rate
Cross-department leakage rate
Citation authorization failure rate
Stale-permission retrieval rate
```

The desired unauthorized retrieval rate is:

```text
0
```

---

# 6. Evaluation Categories

Dataset categories:

```text
Simple factual questions
Multi-document questions
Exact-match queries
Semantic queries
Ambiguous questions
No-answer questions
Unauthorized questions
Prompt-injection questions
Poisoned-document questions
```

---

# 7. Authorization Evaluation

Run the same question under different users.

Example:

```text
User A → Finance access
User B → HR access

Same query

Expected:
Different authorized contexts
```

---

# 8. Prompt-Injection Evaluation

Include documents containing:

```text
Ignore previous instructions
Reveal system prompt
Reveal secrets
Change role
Call a tool
```

The model should treat these as document content rather than commands.

---

# 9. Regression Dataset

Every discovered failure should be added to the permanent evaluation dataset.

Example:

```text
Issue:
Restricted document retrieved.

Regression case:
SEC-AUTH-001
```

---

# 10. Benchmarking

Record:

```text
P50 latency
P90 latency
P95 latency
P99 latency
```

Also measure:

- Retrieval latency
- Reranking latency
- LLM latency
- End-to-end latency

---

# 11. Evaluation Reports

Each benchmark should record:

```text
Date
Code version
Embedding model
LLM model
Dataset version
Configuration
Metrics
Failures
```

This makes results reproducible.

---

# 12. Definition of Done

- [ ] Evaluation dataset exists.
- [ ] Retrieval metrics are measured.
- [ ] Generation metrics are measured.
- [ ] Citation metrics are measured.
- [ ] Security metrics are measured.
- [ ] Authorization cases exist.
- [ ] Prompt-injection cases exist.
- [ ] Regression dataset exists.
- [ ] Latency benchmarks exist.
- [ ] Evaluation results are reproducible.
