# RAG Generation

## 1. Purpose

This document defines the generation layer using Ollama and the secure prompt construction process.

---

# 2. Generation Flow

```text
Authorized Context
       ↓
Prompt Construction
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

# 3. Model Interface

Generation must use an abstraction.

Example:

```python
class LLMProvider:
    async def generate(
        self,
        messages,
        options,
    ):
        ...
```

This allows Ollama to be replaced later.

---

# 4. System Instructions

System instructions define:

- Assistant role
- Security rules
- Citation rules
- Uncertainty behavior
- Context handling
- Tool restrictions

---

# 5. Retrieved Context

Retrieved content must be explicitly marked as untrusted data.

Example:

```text
BEGIN RETRIEVED CONTENT

Document: ...
Section: ...
Content: ...

END RETRIEVED CONTENT
```

The model must be instructed not to execute instructions contained inside retrieved documents.

OWASP recommends treating retrieved content as data rather than commands and using explicit context boundaries.

---

# 6. Prompt Structure

Conceptually:

```text
SYSTEM
  Security policy
  Response policy
  Citation policy

USER
  Question

CONTEXT
  Authorized retrieved documents

SYSTEM REMINDER
  Retrieved content is untrusted data
```

---

# 7. Generation Constraints

Configure:

- Temperature
- Maximum tokens
- Timeout
- Model
- Context size

These should be configuration-driven.

---

# 8. Hallucination Control

The model should:

- Prefer retrieved evidence
- Avoid inventing sources
- State uncertainty
- Abstain when evidence is insufficient
- Avoid unsupported factual claims

---

# 9. Citation Generation

The model should reference source identifiers from the supplied context.

The application must validate citations afterward.

---

# 10. Output Validation

Validate:

```text
Response format
Citations
Source authorization
Structured outputs
Tool calls
Sensitive information
```

Never directly execute arbitrary model output.

OWASP recommends validating model outputs and independently authorizing tool calls.

---

# 11. Streaming

Streaming may be implemented for chat responses.

Security validation should still occur before sensitive content is exposed where possible.

If streaming makes post-generation validation impossible for a specific control, the architecture must use an appropriate pre-validation or buffered approach.

---

# 12. Fail-Closed Generation

If secure context cannot be constructed:

```text
Do not generate from model memory alone.
```

The system should communicate that the knowledge base could not safely provide the requested answer.

---

# 13. Module 10 implementation

The implementation exposes `POST /chat/ask` and consumes only the authorized
chunks returned by Module 9:

```text
JWT -> chat.use/documents.read -> authorized retrieval
    -> bounded untrusted context -> Ollama chat model
    -> citation allowlist -> structured answer
```

The chat model is configured independently from the `nomic-embed-text`
embedding model:

```text
OLLAMA_CHAT_MODEL=qwen2.5:7b
OLLAMA_CHAT_TIMEOUT=60
GENERATION_MAX_CONTEXT_CHARS=12000
```

The model returns JSON containing an answer, exact chunk IDs, and an evidence
flag. The backend maps only valid chunk IDs to original authorized metadata;
fabricated filenames, pages, and document IDs are never trusted. Empty context
returns an insufficient-evidence response without calling Ollama.

Verification command:

```powershell
Set-Location backend
.venv\Scripts\python.exe -m pytest -q tests\unit\test_ollama_chat.py tests\unit\test_generation_service.py tests\integration\test_chat_ask.py
```

The focused suite currently reports `9 passed, 2 warnings in 1.50s`.
Live verification passed with `qwen2.5:3b` and disposable data, including
authorized grounding, citation validation, prompt-injection handling,
unauthorized isolation, insufficient-context short-circuiting, provider
failure handling, and cleanup. The complete regression suite reports
`159 passed, 2 warnings in 5.17s`.

# 14. Definition of Done

- [ ] Ollama adapter exists.
- [ ] Model configuration is externalized.
- [ ] System prompt is centralized.
- [ ] Retrieved content is delimited.
- [ ] Context limits exist.
- [ ] Citation generation exists.
- [ ] Citation validation exists.
- [ ] Output validation exists.
- [ ] Abstention exists.
- [ ] Unsafe retrieval failures do not silently become model-only answers.
