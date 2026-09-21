# Development Phases

## 1. Purpose

This document is the master development roadmap for the Private Enterprise AI Platform.

The project is developed incrementally. Each phase contains multiple modules, and each module must satisfy its own Definition of Done before the project moves forward.

The architecture and implementation should prioritize:

- Security
- Privacy
- Modularity
- Testability
- Maintainability
- Provider abstraction
- Permission-aware AI
- Production readiness

---

# 2. Development Rules

The following rules apply to every phase.

### Rule 1 — One module at a time

Implementation should proceed module by module.

A module is not considered complete until its tests and security review are completed.

### Rule 2 — Define the contract first

Before implementing a module, document:

- Purpose
- Inputs
- Outputs
- Dependencies
- Interfaces
- Security considerations
- Failure behavior
- Testing requirements

### Rule 3 — Security is part of the architecture

Security cannot be added only at the end.

Authorization, validation, logging, privacy, and failure handling must be considered while each module is implemented.

### Rule 4 — Authorization before generation

Unauthorized information must never reach the LLM.

The LLM is not an authorization boundary.

The required flow is:

```text
User
  ↓
Authentication
  ↓
Identity
  ↓
Authorization
  ↓
Permission Filtering
  ↓
Retrieval
  ↓
Authorized Context
  ↓
LLM
  ↓
Response
```

### Rule 5 — Provider abstraction

AI infrastructure must use interfaces where practical.

Examples:

```text
LLMProvider
    └── OllamaProvider

EmbeddingProvider
    └── SentenceTransformerProvider

Retriever
    ├── VectorRetriever
    ├── KeywordRetriever
    └── HybridRetriever
```

The application should not become tightly coupled to one model or vendor.

### Rule 6 — Test before moving forward

Every module should have appropriate tests before dependent modules are implemented.

### Rule 7 — Fail securely

When the system cannot determine whether an operation is authorized or safe, it should fail closed rather than expose information.

### Rule 8 — Minimize sensitive logging

Logs must contain enough information for debugging and auditing without unnecessarily storing:

- Passwords
- Tokens
- Full document contents
- Sensitive user data
- Full prompts containing confidential information

---

# 3. Phase Overview

| Phase | Name                        | Main Objective                               |
| ----- | --------------------------- | -------------------------------------------- |
| 0     | Architecture & Environment  | Establish repository and infrastructure      |
| 1     | Backend Foundation          | Build FastAPI application foundation         |
| 2     | Database & Identity         | Implement users, roles, and persistence      |
| 3     | Authorization & RBAC        | Enforce permissions                          |
| 4     | Document Ingestion          | Process enterprise documents                 |
| 5     | Embeddings & Vector Storage | Index document chunks                        |
| 6     | Basic Retrieval             | Implement retrieval pipeline                 |
| 7     | Permission-Aware Retrieval  | Enforce permissions inside RAG               |
| 8     | Local LLM & Generation      | Generate grounded answers                    |
| 9     | Secure RAG Pipeline         | Connect the complete RAG flow                |
| 10    | Security Hardening          | Defend against common AI/application attacks |
| 11    | LangGraph Agent Layer       | Add controlled orchestration                 |
| 12    | Frontend                    | Build the user interface                     |
| 13    | Admin & Observability       | Add administration and monitoring            |
| 14    | Testing & Evaluation        | Measure quality and security                 |
| 15    | Deployment                  | Package and deploy the platform              |

---

# 4. Phase 0 — Architecture & Development Environment

## Objective

Establish the repository structure, documentation, environment configuration, and local infrastructure.

## Modules

### Module 0.1 — Repository Structure

Create the project structure and documentation framework.

### Module 0.2 — Environment Configuration

Define environment variables and configuration conventions.

### Module 0.3 — Docker Compose

Configure:

- PostgreSQL
- Qdrant
- Ollama

### Module 0.4 — Development Documentation

Document:

- Local setup
- Architecture
- Services
- Development workflow

## Definition of Done

- [ ] Repository structure exists
- [ ] Documentation structure exists
- [ ] `.env.example` exists
- [ ] Secrets are excluded from Git
- [ ] Docker Compose starts successfully
- [ ] PostgreSQL is reachable
- [ ] Qdrant is reachable
- [ ] Ollama is reachable
- [ ] Local development instructions exist
- [ ] No production secrets are committed

---

# 5. Phase 1 — Backend Foundation

## Objective

Create a stable FastAPI application foundation.

## Modules

### Module 1.1 — Application Entry Point

Implement the FastAPI application.

### Module 1.2 — Configuration

Implement centralized environment-based configuration.

### Module 1.3 — Logging

Implement structured application logging.

### Module 1.4 — Error Handling

Implement consistent API error responses.

### Module 1.5 — Database Connection

Create the PostgreSQL connection layer.

### Module 1.6 — Health Checks

Provide service health endpoints.

### Module 1.7 — API Versioning

Establish versioned API routes.

## Definition of Done

- [ ] FastAPI application starts
- [ ] Configuration loads from environment
- [ ] `/health` works
- [ ] Database health can be checked
- [ ] Structured logging works
- [ ] API errors use a consistent format
- [ ] API routes are versioned
- [ ] Basic backend tests pass

---

# 6. Phase 2 — Database & Identity

## Objective

Implement persistent identity and the core database model.

## Modules

### Module 2.1 — Database Models

Implement:

- User
- Role
- Department
- Document
- Permission
- Audit Log

### Module 2.2 — Database Migrations

Introduce migration management.

### Module 2.3 — Password Security

Implement secure password hashing.

### Module 2.4 — Authentication

Implement authentication and JWT handling.

### Module 2.5 — Identity Resolution

Resolve the authenticated user from a request.

## Definition of Done

- [ ] Database schema exists
- [ ] Migrations work
- [ ] Passwords are never stored in plaintext
- [ ] Authentication works
- [ ] JWT expiration is enforced
- [ ] Protected endpoints require authentication
- [ ] Authenticated identity is available to services
- [ ] Database constraints exist
- [ ] Relevant indexes exist
- [ ] Authentication tests pass

---

# 7. Phase 3 — Authorization & RBAC

## Objective

Create the authorization system that controls access to enterprise resources.

## Modules

### Module 3.1 — Roles

Implement role definitions and policies.

Initial roles:

```text
ADMIN
MANAGER
EMPLOYEE
```

### Module 3.2 — Departments

Implement department membership.

Initial departments:

```text
HR
Finance
Engineering
Sales
Legal
```

### Module 3.3 — Permission Model

Implement document and resource permissions.

### Module 3.4 — Permission Service

Centralize authorization decisions.

### Module 3.5 — API Authorization

Protect API operations using authorization dependencies.

### Module 3.6 — Denied Access Handling

Implement secure access-denied responses.

## Definition of Done

- [ ] Roles exist
- [ ] Departments exist
- [ ] Users can belong to departments
- [ ] Permissions are persisted
- [ ] Authorization decisions are server-side
- [ ] Unauthorized access is rejected
- [ ] Authorization cannot be bypassed through RAG
- [ ] Authorization tests pass
- [ ] Security tests cover privilege boundaries

---

# 8. Phase 4 — Document Ingestion

## Objective

Build a reliable pipeline for converting enterprise documents into searchable chunks.

## Supported Formats

Initial support:

```text
PDF
DOCX
TXT
Markdown
```

## Modules

### Module 4.1 — File Validation

Validate:

- File type
- File size
- File name
- File content
- Upload constraints

### Module 4.2 — Document Loaders

Implement format-specific loading.

### Module 4.3 — Text Extraction

Extract usable document text.

### Module 4.4 — Cleaning

Normalize extracted content.

### Module 4.5 — Metadata Extraction

Attach metadata such as:

```text
document_id
department
owner
classification
source
page
section
chunk_id
```

### Module 4.6 — Chunking

Create deterministic document chunks.

### Module 4.7 — Persistence

Persist document and chunk metadata.

### Module 4.8 — Ingestion Pipeline

Connect all ingestion stages.

## Definition of Done

- [ ] Supported files can be uploaded
- [ ] Unsupported files are rejected
- [ ] File size limits are enforced
- [ ] Text extraction works
- [ ] Cleaning is deterministic
- [ ] Chunking is deterministic
- [ ] Metadata is attached
- [ ] Documents are persisted
- [ ] Failures do not leave inconsistent state
- [ ] Malicious file considerations are addressed
- [ ] Unit tests pass

---

# 9. Phase 5 — Embeddings & Vector Storage

## Objective

Convert document chunks into embeddings and store them in Qdrant.

## Modules

### Module 5.1 — Embedding Interface

Define the `EmbeddingProvider` abstraction.

### Module 5.2 — Local Embedding Provider

Implement Sentence Transformers.

### Module 5.3 — Qdrant Integration

Implement Qdrant client integration.

### Module 5.4 — Collection Management

Create and manage collections.

### Module 5.5 — Vector Indexing

Store chunk embeddings and metadata.

### Module 5.6 — Reindexing

Make indexing idempotent and reindex-safe.

## Definition of Done

- [ ] Embedding provider is abstracted
- [ ] Chunks can be embedded
- [ ] Embeddings are stored in Qdrant
- [ ] Metadata is stored with vectors
- [ ] Collection configuration is deterministic
- [ ] Re-indexing does not create uncontrolled duplicates
- [ ] Qdrant failures are handled
- [ ] Tests pass

---

# 10. Phase 6 — Basic Retrieval

## Objective

Build retrieval independently from the LLM.

## Modules

### Module 6.1 — Vector Retrieval

Retrieve chunks using semantic similarity.

### Module 6.2 — Keyword Retrieval

Retrieve chunks using lexical matching.

### Module 6.3 — Hybrid Retrieval

Combine semantic and keyword retrieval.

### Module 6.4 — Score Fusion

Normalize and combine retrieval results.

### Module 6.5 — Reranking

Improve ranking using a reranker.

### Module 6.6 — Retrieval Configuration

Centralize retrieval parameters.

## Definition of Done

- [ ] Vector retrieval works
- [ ] Keyword retrieval works
- [ ] Hybrid retrieval works
- [ ] Results contain scores
- [ ] Results contain metadata
- [ ] Reranking works
- [ ] Retrieval works without an LLM
- [ ] Retrieval latency is measurable
- [ ] Relevance tests exist

---

# 11. Phase 7 — Permission-Aware Retrieval

## Objective

Integrate authorization directly into the retrieval layer.

This is one of the most important security phases.

## Modules

### Module 7.1 — Permission Resolution

Resolve the user's effective permissions.

### Module 7.2 — Retrieval Filters

Translate permissions into retrieval constraints.

### Module 7.3 — Qdrant Metadata Filtering

Apply authorization filters during vector retrieval.

### Module 7.4 — Authorized Hybrid Retrieval

Ensure both retrieval strategies respect authorization.

### Module 7.5 — Security Tests

Verify unauthorized information cannot enter the RAG context.

## Required Security Boundary

```text
User
 ↓
Authentication
 ↓
Authorization
 ↓
Permission Filter
 ↓
Retrieval
 ↓
Authorized Results
 ↓
LLM
```

Never:

```text
User
 ↓
Retrieve Everything
 ↓
LLM
 ↓
"Please don't reveal confidential information"
```

## Definition of Done

- [ ] Department restrictions work
- [ ] Role restrictions work
- [ ] Document permissions work
- [ ] Classification restrictions work
- [ ] Unauthorized chunks are filtered before generation
- [ ] Unauthorized chunks cannot enter prompts
- [ ] Security tests prove the boundary
- [ ] RAG cannot bypass authorization

---

# 12. Phase 8 — Local LLM & Generation

## Objective

Add local LLM generation while preserving authorization and grounding.

## Modules

### Module 8.1 — LLM Interface

Define the `LLMProvider` abstraction.

### Module 8.2 — Ollama Provider

Implement local LLM inference through Ollama.

### Module 8.3 — Prompt Construction

Build controlled RAG prompts.

### Module 8.4 — Context Builder

Construct context exclusively from authorized retrieval results.

### Module 8.5 — Grounded Generation

Generate answers using retrieved evidence.

### Module 8.6 — Citations

Return source references with answers.

### Module 8.7 — Abstention

Refuse to answer when evidence is insufficient.

## Definition of Done

- [ ] LLM provider is abstracted
- [ ] Ollama integration works
- [ ] Context builder works
- [ ] Only authorized context reaches the LLM
- [ ] Answers are grounded in retrieved evidence
- [ ] Citations are generated
- [ ] Insufficient evidence triggers abstention
- [ ] LLM failures are handled safely
- [ ] Timeouts are enforced

---

# 13. Phase 9 — Secure RAG Pipeline

## Objective

Connect authentication, authorization, retrieval, generation, validation, and auditing into one controlled pipeline.

## Pipeline

```text
Request
   ↓
Authentication
   ↓
Query Validation
   ↓
Query Analysis
   ↓
Authorization
   ↓
Permission-Aware Retrieval
   ↓
Hybrid Retrieval
   ↓
Reranking
   ↓
Context Validation
   ↓
Prompt Construction
   ↓
Local LLM
   ↓
Output Validation
   ↓
Citation Validation
   ↓
Audit Logging
   ↓
Response
```

## Definition of Done

- [ ] End-to-end RAG works
- [ ] Authorization happens before context construction
- [ ] Unauthorized chunks cannot reach the LLM
- [ ] Hybrid retrieval works
- [ ] Reranking works
- [ ] Citations work
- [ ] Abstention works
- [ ] Errors are handled
- [ ] Requests are auditable
- [ ] Integration tests pass

---

# 14. Phase 10 — Security Hardening

## Objective

Defend the application against common application and AI-specific attacks.

## Modules

### Module 10.1 — Prompt Injection Defense

Detect and mitigate malicious instructions in:

- User queries
- Retrieved documents
- Metadata
- Tool outputs

### Module 10.2 — Input Validation

Validate API and AI inputs.

### Module 10.3 — File Security

Defend against malicious uploads.

### Module 10.4 — Rate Limiting

Protect expensive endpoints.

### Module 10.5 — Output Validation

Validate generated responses.

### Module 10.6 — Resource Limits

Prevent excessive:

- File sizes
- Query sizes
- Retrieval counts
- Context sizes
- Generation lengths

### Module 10.7 — Security Logging

Record security-relevant events.

## Definition of Done

- [ ] Prompt injection tests exist
- [ ] Unauthorized retrieval tests exist
- [ ] Malicious document tests exist
- [ ] Oversized upload tests exist
- [ ] Invalid file type tests exist
- [ ] Authentication abuse tests exist
- [ ] Rate limiting works
- [ ] Malformed requests are rejected
- [ ] Security events are logged
- [ ] Failures default to safe behavior

---

# 15. Phase 11 — LangGraph Agent Layer

## Objective

Introduce controlled agent orchestration without allowing agents to bypass security controls.

## Graph

```text
START
  ↓
Query Analysis
  ↓
Authorization
  ↓
Retrieval
  ↓
Validation
  ↓
Generation
  ↓
Citation Validation
  ↓
END
```

## Modules

### Module 11.1 — Agent State

Define strongly typed graph state.

### Module 11.2 — Query Analysis Node

Analyze the user's request.

### Module 11.3 — Retrieval Node

Execute authorized retrieval.

### Module 11.4 — Validation Node

Validate evidence and intermediate state.

### Module 11.5 — Generation Node

Generate grounded output.

### Module 11.6 — Citation Validation Node

Validate source references.

## Definition of Done

- [ ] State is typed
- [ ] Nodes have clear responsibilities
- [ ] Authorization is mandatory
- [ ] Agent cannot bypass permission filtering
- [ ] State contains only necessary information
- [ ] Retry behavior is controlled
- [ ] Failure behavior is deterministic
- [ ] Nodes can be tested independently

---

# 16. Phase 12 — Frontend

## Objective

Build the user-facing enterprise AI application.

## Modules

### Module 12.1 — Authentication UI

Login and session management.

### Module 12.2 — Chat Interface

Enterprise AI chat.

### Module 12.3 — Citations

Display source documents and references.

### Module 12.4 — Document Management

Upload and manage authorized documents.

### Module 12.5 — Admin Interface

Administrative functionality.

### Module 12.6 — Error Handling

Display safe user-facing errors.

## Definition of Done

- [ ] Login works
- [ ] Protected routes work
- [ ] Chat works
- [ ] Citations are displayed
- [ ] Document permissions are respected
- [ ] Admin routes are protected
- [ ] No secrets are exposed in frontend code
- [ ] API errors are handled

---

# 17. Phase 13 — Administration & Observability

## Objective

Provide enterprise administration and system visibility.

## Modules

### Module 13.1 — User Administration

Manage users, roles, and departments.

### Module 13.2 — Document Administration

Manage indexed documents.

### Module 13.3 — Permission Administration

Manage document access policies.

### Module 13.4 — Audit Logs

Search and inspect security-relevant activity.

### Module 13.5 — System Health

Monitor:

- API
- PostgreSQL
- Qdrant
- Ollama

### Module 13.6 — AI Metrics

Monitor:

- Retrieval latency
- Generation latency
- Token usage where available
- Retrieval counts
- Failure rates
- Citation validation failures

## Definition of Done

- [ ] Admin dashboard exists
- [ ] Users can be managed
- [ ] Documents can be managed
- [ ] Permissions can be managed
- [ ] Audit logs are searchable
- [ ] System health is visible
- [ ] AI metrics are available
- [ ] Sensitive information is not unnecessarily exposed

---

# 18. Phase 14 — Testing & Evaluation

## Objective

Measure application correctness, retrieval quality, security, and AI behavior.

## Evaluation Categories

### Retrieval Quality

- Relevant document retrieval
- Ranking quality
- Hybrid retrieval effectiveness

### Answer Quality

- Correctness
- Groundedness
- Completeness

### Citation Quality

- Citation correctness
- Citation relevance
- Citation completeness

### Authorization

- Authorized retrieval
- Unauthorized retrieval prevention
- Cross-department isolation
- Role isolation

### Security

- Prompt injection
- Malicious documents
- Authentication abuse
- Input attacks

### Performance

- Retrieval latency
- Generation latency
- End-to-end latency
- Resource consumption

## Evaluation Dataset

The test dataset should contain:

```text
Normal questions
Exact-match questions
Multi-hop questions
No-answer questions
Ambiguous questions
Unauthorized questions
Prompt-injection questions
Document-injection questions
```

## Definition of Done

- [ ] Unit tests exist
- [ ] Integration tests exist
- [ ] Authorization tests exist
- [ ] Security regression tests exist
- [ ] Retrieval evaluation exists
- [ ] Groundedness evaluation exists
- [ ] Citation evaluation exists
- [ ] Performance measurements exist
- [ ] CI test execution is configured

---

# 19. Phase 15 — Deployment

## Objective

Package the complete platform for reproducible deployment.

## Target Architecture

```text
                 ┌───────────────┐
                 │ Reverse Proxy │
                 └───────┬───────┘
                         │
              ┌──────────┴──────────┐
              │                     │
        ┌─────▼─────┐        ┌─────▼─────┐
        │  Next.js  │        │  FastAPI  │
        └───────────┘        └─────┬─────┘
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                │
             ┌────▼────┐      ┌────▼────┐     ┌────▼────┐
             │Postgres │      │  Qdrant │     │ Ollama  │
             └─────────┘      └─────────┘     └─────────┘
```

## Modules

### Module 15.1 — Production Docker Configuration

### Module 15.2 — Reverse Proxy

### Module 15.3 — Persistent Storage

### Module 15.4 — Secrets Configuration

### Module 15.5 — Health Checks

### Module 15.6 — Backup Strategy

### Module 15.7 — Deployment Documentation

## Definition of Done

- [ ] Complete stack starts through Docker
- [ ] Persistent volumes are configured
- [ ] Health checks work
- [ ] Secrets are externalized
- [ ] Database backup procedure exists
- [ ] Vector database backup procedure exists
- [ ] Deployment documentation exists
- [ ] Production configuration is separated from development configuration

---

# 20. Final Project Definition of Done

The platform is considered complete when the following capabilities are operational and tested.

## Application

- [ ] FastAPI backend
- [ ] Next.js frontend
- [ ] PostgreSQL
- [ ] Qdrant
- [ ] Ollama
- [ ] Docker deployment

## Identity & Access

- [ ] Authentication
- [ ] JWT
- [ ] Password hashing
- [ ] RBAC
- [ ] Departments
- [ ] Document-level authorization

## RAG

- [ ] Document ingestion
- [ ] Chunking
- [ ] Embeddings
- [ ] Vector search
- [ ] Keyword search
- [ ] Hybrid retrieval
- [ ] Reranking
- [ ] Permission-aware retrieval
- [ ] Grounded generation
- [ ] Citations
- [ ] Abstention

## Security

- [ ] Prompt injection defenses
- [ ] File validation
- [ ] Input validation
- [ ] Rate limiting
- [ ] Output validation
- [ ] Resource limits
- [ ] Audit logging
- [ ] Unauthorized context prevention

## AI

- [ ] Local LLM inference
- [ ] Provider abstraction
- [ ] LangGraph orchestration
- [ ] Controlled agent state
- [ ] AI evaluation

## Operations

- [ ] Admin dashboard
- [ ] Health monitoring
- [ ] AI metrics
- [ ] Security logs
- [ ] Backups
- [ ] Deployment documentation

## Quality

- [ ] Unit tests
- [ ] Integration tests
- [ ] Security tests
- [ ] Retrieval evaluation
- [ ] Groundedness evaluation
- [ ] Citation evaluation
- [ ] Performance evaluation
- [ ] CI

---

# 21. Development Workflow

Every development session should follow this process:

```text
1. Identify current phase
        ↓
2. Identify current module
        ↓
3. Read relevant architecture documentation
        ↓
4. Define module contract
        ↓
5. Implement module
        ↓
6. Write tests
        ↓
7. Run tests
        ↓
8. Perform security review
        ↓
9. Update documentation
        ↓
10. Update progress.md
        ↓
11. Mark module complete
        ↓
12. Move to next module
```

No dependent module should be implemented before its required dependency is stable unless the dependency is explicitly mocked or abstracted for testing.
