# Private Enterprise AI Platform — Documentation

## Purpose

This directory contains the technical documentation for the Private Enterprise AI Platform.

The documentation is organized by responsibility so that architecture, security, RAG, development, and deployment decisions remain independent and maintainable.

The documentation is the **source of truth for architectural decisions**.

Implementation should follow these documents, and documentation should be updated when the architecture changes.

---

# Documentation Structure

```text
docs/
│
├── README.md
│
├── architecture/
│   ├── system.md
│   ├── backend.md
│   ├── frontend.md
│   ├── rag.md
│   ├── data-model.md
│   └── integrations.md
│
├── security/
│   ├── security-architecture.md
│   ├── authentication.md
│   ├── authorization.md
│   ├── prompt-injection.md
│   └── threat-model.md
│
├── development/
│   ├── phases.md
│   ├── progress.md
│   ├── coding-standards.md
│   └── testing-strategy.md
│
├── rag/
│   ├── ingestion.md
│   ├── retrieval.md
│   ├── embeddings.md
│   ├── generation.md
│   └── evaluation.md
│
└── deployment/
    ├── local-development.md
    ├── docker.md
    └── production.md
```

---

# 1. Architecture

The `architecture/` directory describes the structure of the application and how its components interact.

### `architecture/system.md`

Defines the complete system architecture.

Contains:

- High-level architecture
- Component relationships
- Request flow
- RAG flow
- Security boundaries
- External/internal services
- Major architectural decisions

### `architecture/backend.md`

Defines the backend architecture.

Contains:

- FastAPI structure
- API layers
- Services
- Database layer
- Dependency injection
- Backend module boundaries

### `architecture/frontend.md`

Defines the frontend architecture.

Contains:

- Next.js structure
- Feature organization
- API communication
- Authentication state
- Protected routes
- UI responsibilities

### `architecture/rag.md`

Defines the high-level RAG architecture.

Contains:

- Ingestion
- Embeddings
- Retrieval
- Authorization
- Reranking
- Generation
- Citations

Detailed RAG behavior belongs in the `rag/` directory.

### `architecture/data-model.md`

Defines the conceptual data model.

Contains:

- Users
- Roles
- Departments
- Documents
- Permissions
- Chunks
- Audit logs
- Relationships
- Important constraints

### `architecture/integrations.md`

Documents external and infrastructure integrations.

Initial integrations:

- PostgreSQL
- Qdrant Cloud
- Ollama
- Sentence Transformers
- Docker

---

# 2. Security

The `security/` directory defines the platform's security model.

Security is treated as a cross-cutting architectural concern rather than an isolated feature.

### `security/security-architecture.md`

Defines the overall security architecture.

### `security/authentication.md`

Defines:

- Password handling
- JWT
- Sessions/tokens
- Identity resolution
- Authentication failures

### `security/authorization.md`

Defines:

- RBAC
- Departments
- Permissions
- Document access
- Authorization flow
- Permission-aware retrieval

This document is especially important because authorization must occur **before information reaches the LLM**.

### `security/prompt-injection.md`

Defines defenses against:

- User prompt injection
- Document prompt injection
- Indirect prompt injection
- Malicious retrieved content
- Instruction/data separation

### `security/threat-model.md`

Documents:

- Assets
- Attack surfaces
- Threat actors
- Threat scenarios
- Mitigations
- Residual risks

---

# 3. Development

The `development/` directory controls how the project is built.

### `development/phases.md`

The master project roadmap.

Contains:

- Development phases
- Modules
- Dependencies
- Definitions of Done
- Development workflow

### `development/progress.md`

The project handoff document.

It records:

- Current phase
- Current module
- Completed work
- Open issues
- Architecture decisions
- Next task
- Session history

This file must be updated after meaningful development sessions.

### `development/coding-standards.md`

Defines coding conventions and engineering standards.

### `development/testing-strategy.md`

Defines:

- Unit testing
- Integration testing
- Security testing
- RAG evaluation
- AI evaluation
- Performance testing
- CI testing

---

# 4. RAG

The `rag/` directory contains detailed technical documentation for the Retrieval-Augmented Generation system.

### `rag/ingestion.md`

Defines the document ingestion pipeline:

```text
File
 ↓
Validation
 ↓
Loading
 ↓
Extraction
 ↓
Cleaning
 ↓
Metadata
 ↓
Chunking
 ↓
Persistence
```

### `rag/retrieval.md`

Defines:

- Vector retrieval
- Keyword retrieval
- Hybrid retrieval
- Score fusion
- Reranking
- Retrieval configuration
- Permission-aware retrieval

### `rag/embeddings.md`

Defines:

- Embedding interface
- Embedding models
- Vector dimensions
- Similarity metrics
- Qdrant Cloud storage
- Reindexing

### `rag/generation.md`

Defines:

- LLM provider interface
- Ollama integration
- Prompt construction
- Context construction
- Grounded generation
- Citations
- Abstention

### `rag/evaluation.md`

Defines how RAG quality is measured.

Metrics may include:

- Retrieval relevance
- Recall
- Precision
- Groundedness
- Answer correctness
- Citation correctness
- Latency

---

# 5. Deployment

The `deployment/` directory documents how the platform is run.

### `deployment/local-development.md`

Defines the local developer workflow.

Contains:

- Prerequisites
- Environment setup
- Service startup
- Database setup
- Testing
- Development commands

### `deployment/docker.md`

Defines Docker architecture.

Contains:

- Dockerfiles
- Docker Compose
- Networks
- Volumes
- Health checks
- Environment variables

### `deployment/production.md`

Defines the eventual production deployment architecture.

Contains:

- Production topology
- Reverse proxy
- Secrets
- Persistent storage
- Backups
- Monitoring
- Scaling considerations

---

# 6. Documentation Rules

## Rule 1 — One responsibility per document

A document should have a clear purpose.

Avoid turning individual files into large collections of unrelated information.

## Rule 2 — Architecture before implementation

Important architectural decisions should be documented before implementing the corresponding module.

## Rule 3 — Documentation follows implementation

If implementation changes an architectural decision, update the relevant documentation.

## Rule 4 — No duplicated source of truth

A decision should have one authoritative location.

Other documents may reference that decision instead of duplicating it.

## Rule 5 — Security decisions are explicit

Security-sensitive behavior must be documented rather than left implicit in implementation.

## Rule 6 — Keep progress separate

`development/progress.md` records the current project state.

It should not become a replacement for architecture documentation.

---

# 7. Architectural Principles

The platform follows these principles.

### Security by Design

Security requirements are considered during architecture and implementation.

### Least Privilege

Users should have only the access required for their role.

### Authorization Before Generation

Unauthorized information must never reach the LLM.

### Provider Independence

AI providers should be replaceable where practical.

### Modular Design

Components should have clear responsibilities and interfaces.

### Testability

Core components should be independently testable.

### Deterministic Pipelines

Agentic behavior should only be introduced where it provides meaningful value.

### Local-First AI

Sensitive enterprise data should remain within the organization's infrastructure whenever possible.

### Observability

Important system behavior should be measurable and auditable.

### Fail Securely

Security-sensitive failures should default to denying access rather than exposing information.

---

# 8. Technology Stack

| Layer               | Technology                  |
| ------------------- | --------------------------- |
| Backend             | Python / FastAPI            |
| Database            | PostgreSQL                  |
| ORM                 | SQLAlchemy                  |
| Migrations          | Alembic                     |
| Vector Database     | Qdrant Cloud                      |
| LLM Runtime         | Ollama                      |
| Embeddings          | Sentence Transformers       |
| Agent Orchestration | LangGraph                   |
| Frontend            | Next.js / TypeScript        |
| Styling             | Tailwind CSS                |
| Infrastructure      | Docker / Docker Compose     |
| Authentication      | JWT                         |
| Authorization       | RBAC + resource permissions |

The exact model versions and provider configurations are documented separately when finalized.

---

# 9. Critical Data Flow

The most security-sensitive data flow is:

```text
User Query
    │
    ▼
Authentication
    │
    ▼
Identity Resolution
    │
    ▼
Authorization
    │
    ▼
Permission Filter
    │
    ▼
Retrieval
    │
    ▼
Authorized Context
    │
    ▼
LLM
    │
    ▼
Validated Response
    │
    ▼
Audit Log
```

The following architecture is explicitly prohibited:

```text
User
  ↓
Retrieve all documents
  ↓
LLM
  ↓
"Do not reveal confidential information"
```

The LLM must never be responsible for enforcing access control.

---

# 10. Development Workflow

Every module follows:

```text
Architecture
    ↓
Module Contract
    ↓
Implementation
    ↓
Unit Tests
    ↓
Integration Tests
    ↓
Security Review
    ↓
Documentation Update
    ↓
Progress Update
    ↓
Next Module
```

A module is complete only when its Definition of Done is satisfied.

---

# 11. Current Project State

For the current implementation status, see:

`development/progress.md`

For the complete roadmap, see:

`development/phases.md`
