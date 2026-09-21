# System Architecture

## 1. Purpose

This document defines the high-level architecture of the Private Enterprise AI Platform after the migration to Supabase.

It describes the major components, responsibilities, data flows, security boundaries, infrastructure dependencies, and architectural principles used by the platform.

Detailed implementation decisions are documented in the corresponding architecture, security, RAG, and deployment documents.

---

# 2. System Overview

The Private Enterprise AI Platform allows authenticated users to interact with internal company knowledge through a secure Retrieval-Augmented Generation pipeline.

The platform combines:

- Next.js for the user interface
- Supabase Auth for authentication, sessions, and JWT issuance
- Supabase PostgreSQL for relational application state
- Supabase Storage for uploaded enterprise documents
- FastAPI for business logic, authorization, ingestion, and RAG orchestration
- Qdrant Cloud for vector search
- Ollama for local LLM inference
- LangGraph for controlled orchestration after the deterministic pipeline is stable
- Audit logging and security controls

The primary security objective is:

> No information should reach the LLM unless the requesting user is authorized to access that information.

Authentication and authorization are different. Supabase Auth establishes identity. FastAPI enforces the application's authorization policy.

---

# 3. High-Level Architecture

```text
                    ┌─────────────────────┐
                    │      Next.js        │
                    │      Frontend       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Supabase       │
                    │                     │
                    │  Supabase Auth      │
                    │  PostgreSQL         │
                    │  Storage            │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │                     │
                    │ Authentication      │
                    │ Authorization       │
                    │ Business Logic      │
                    │ RAG Orchestration   │
                    └──────┬────────┬─────┘
                           │        │
                           ▼        ▼
                    ┌──────────┐ ┌──────────┐
                    │  Qdrant Cloud  │ │  Ollama  │
                    │ Vectors  │ │ Local LLM│
                    └──────────┘ └──────────┘
```

The default deployment assumes Supabase is external or managed. Docker runs the application services that remain under local control:

```text
backend
frontend
qdrant
ollama
```

Self-hosted Supabase may be documented later as an optional deployment model, not the default.

---

# 4. Main Request Flow

```text
User
 ↓
Next.js
 ↓
Supabase Auth
 ↓
JWT
 ↓
FastAPI
 ↓
Identity Resolution
 ↓
Application Authorization
 ↓
Permission-Aware Retrieval
 ↓
Qdrant Cloud
 ↓
Authorized Context
 ↓
Ollama
 ↓
Response + Citations
```

The frontend may use Supabase client-side APIs for authentication and session handling. Protected business operations still go through FastAPI.

---

# 5. Component Responsibilities

## 5.1 Next.js Frontend

Responsibilities:

- Authentication UI using Supabase Auth
- Session-aware user experience
- Chat interface
- Document management UI
- Citation display
- User-facing errors
- Administrative interface
- System monitoring interface

The frontend is not a security boundary. It must not contain service-role keys or enforce final authorization decisions.

## 5.2 Supabase Auth

Supabase Auth handles:

- User authentication
- Password management
- Session management
- JWT issuance
- Token refresh
- Authentication lifecycle

The application must not implement custom password authentication, store plaintext passwords, or add a custom password credential column to the application profile table.

## 5.3 Supabase PostgreSQL

Supabase PostgreSQL stores the authoritative relational state:

- `auth.users` managed by Supabase
- `public.profiles`
- Departments
- Roles
- Permissions
- User-role relationships
- Role-permission relationships
- Documents
- Document permissions
- Document chunks
- Audit logs
- Other application metadata

PostgreSQL is authoritative for application metadata and authorization state. It is not the primary vector search engine.

## 5.4 Supabase Storage

Supabase Storage stores uploaded enterprise documents.

It is the primary object store for original files. FastAPI controls document lifecycle operations that require business authorization and ingestion.

## 5.5 FastAPI Backend

FastAPI remains the main application and security boundary.

Responsibilities:

- JWT validation and identity resolution
- Application authorization
- Business logic
- User/profile administration
- Document management
- Supabase Storage ingestion orchestration
- Retrieval orchestration
- Qdrant Cloud filtering
- Ollama interaction
- Audit logging
- Security validation
- Administrative operations
- Health checks

Supabase does not become the business-logic layer.

## 5.6 Qdrant Cloud

Qdrant Cloud stores document chunk embeddings, chunk identifiers, retrieval metadata, and authorization-related metadata required for filtering.

Qdrant Cloud is a derived retrieval index. Supabase PostgreSQL remains the source of truth.

## 5.7 Ollama

Ollama provides local LLM inference through an abstraction:

```text
LLMProvider
      │
      └── OllamaProvider
```

A different local or remote provider may be added later without rewriting the RAG pipeline.

---

# 6. Document Ingestion Flow

```text
Upload
 ↓
Supabase Storage
 ↓
FastAPI ingestion pipeline
 ↓
File validation
 ↓
Parse
 ↓
Clean
 ↓
Chunk
 ↓
Store document and chunk metadata in Supabase PostgreSQL
 ↓
Generate embeddings
 ↓
Index into Qdrant Cloud
 ↓
Mark ingestion complete
```

Each chunk must retain enough metadata to support retrieval, citation, authorization, traceability, and reindexing.

A failed ingestion must not leave the system believing a document is successfully indexed.

---

# 7. Query Flow

```text
User Query
    │
    ▼
Supabase Authentication
    │
    ▼
JWT
    │
    ▼
FastAPI JWT Validation
    │
    ▼
Profile Lookup
    │
    ▼
Input Validation
    │
    ▼
Application Authorization
    │
    ▼
Query Analysis
    │
    ▼
Permission-Aware Retrieval
    │
    ▼
Qdrant Cloud Metadata Filtering
    │
    ▼
Reranking
    │
    ▼
Context Validation
    │
    ▼
Prompt Construction
    │
    ▼
Ollama
    │
    ▼
Output Validation
    │
    ▼
Citation Validation
    │
    ▼
Audit Logging
    │
    ▼
Response
```

---

# 8. Critical Security Boundary

```text
Supabase Auth
      ↓
JWT
      ↓
FastAPI identity
      ↓
FastAPI authorization
      ↓
Supabase RLS where applicable
      ↓
Qdrant Cloud authorization filters
      ↓
Authorized RAG context
      ↓
LLM
```

Authorization must occur before retrieval results are allowed into the generation context.

The LLM must never receive unauthorized enterprise information.

---

# 9. Prohibited Architecture

The following designs are explicitly prohibited:

```text
Supabase Auth
      ↓
LLM
```

```text
User
  │
  ▼
Retrieve all documents
  │
  ▼
LLM
  │
  ▼
"Do not reveal confidential information"
```

Natural-language instructions cannot replace authorization controls.

---

# 10. Authorization-Aware Retrieval

Authorization metadata should be available to the retrieval layer.

Example Qdrant Cloud payload:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "department_id": "...",
  "classification": "INTERNAL"
}
```

Authorization filters must be derived from trusted server-side identity and policy information. A client must never be allowed to submit arbitrary filters such as:

```json
{
  "department_id": "finance"
}
```

and thereby gain access to Finance documents.

---

# 11. Supabase Row Level Security

Supabase Row Level Security is part of the database security layer and should be enabled on appropriate exposed application tables.

RLS is defense in depth. It is not a replacement for FastAPI authorization.

FastAPI must still determine:

- User identity
- Roles
- Department
- Document permissions
- Classification restrictions
- Resource access
- RAG retrieval permissions

---

# 12. Service Boundaries

```text
API Layer
    ↓
Authentication / Identity
    ↓
Application Services
    ↓
Authorization
    ↓
RAG / Domain Logic
    ↓
Infrastructure Abstractions
    ↓
Supabase / Qdrant Cloud / Ollama
```

The exact implementation boundaries are defined in `architecture/backend.md`.

---

# 13. Data Ownership

| Component           | Primary Responsibility                         |
| ------------------- | ---------------------------------------------- |
| Supabase Auth       | Authentication, sessions, JWTs                 |
| Supabase PostgreSQL | Authoritative relational application state     |
| Supabase Storage    | Original uploaded enterprise documents         |
| FastAPI             | Business logic, authorization, RAG orchestration |
| Qdrant Cloud              | Derived vector index and retrieval metadata    |
| Ollama              | Local LLM inference                            |
| Next.js             | User interface                                 |

No component should silently become the source of truth for another component's responsibility.

---

# 14. Document Lifecycle

```text
Upload
  ↓
Supabase Storage persistence
  ↓
Validation
  ↓
Extraction
  ↓
Cleaning
  ↓
Chunking
  ↓
PostgreSQL metadata persistence
  ↓
Embedding
  ↓
Qdrant Cloud indexing
  ↓
Available for permission-controlled retrieval
  ↓
Update / Reindex / Delete
```

Deletion and reindexing must maintain consistency between Supabase PostgreSQL, Supabase Storage, and Qdrant Cloud.

---

# 15. Audit Flow

Security-sensitive operations should produce audit events, including authentication failures, document uploads, document deletions, permission changes, denied document access, RAG queries, security events, and administrative operations.

Audit logging must avoid unnecessarily storing confidential document contents or secrets.

---

# 16. Deployment Architecture

During local development, Docker Compose should run:

```text
Docker Network
│
├── frontend
│
├── backend
│
├── qdrant
│
└── ollama
```

Supabase is external/managed by default and is reached through configured URLs and keys.

Default persistent local volumes:

```text
qdrant_data
ollama_data
```

Do not include a standalone `postgres` service in the default Docker Compose architecture when using Supabase as the database provider.

---

# 17. Security Zones

```text
┌─────────────────────────────────────────────┐
│                  User Zone                  │
│                                             │
│                Next.js UI                   │
└──────────────────────┬──────────────────────┘
                       │
                       │ Supabase Auth / HTTPS
                       ▼
┌─────────────────────────────────────────────┐
│              Supabase Zone                  │
│                                             │
│ Auth        PostgreSQL        Storage       │
└──────────────────────┬──────────────────────┘
                       │ JWT / API / DB access
                       ▼
┌─────────────────────────────────────────────┐
│             Application Zone                │
│                                             │
│                  FastAPI                    │
│                                             │
│ Identity Resolution                         │
│ Authorization                               │
│ RAG Orchestration                           │
│ Security Controls                           │
└───────────┬─────────────────────┬───────────┘
            │                     │
            ▼                     ▼
       Qdrant Cloud Search          Ollama AI
```

FastAPI controls communication between application security decisions, Qdrant Cloud retrieval, and Ollama generation.

---

# 18. Architectural Principles

## Principle 1 - Least Privilege

Every user and service receives only the access required for its responsibilities.

## Principle 2 - Defense in Depth

```text
Supabase Auth
      +
FastAPI Authorization
      +
Supabase RLS
      +
Qdrant Cloud Filtering
      +
Prompt Injection Defense
      +
Output Validation
      +
Audit Logging
```

## Principle 3 - Never Trust the LLM

The model is an untrusted reasoning component. It must not enforce authorization, access control, security policy, or secret management.

## Principle 4 - Minimize Data Exposure

Only the minimum information required for a task should be passed between components.

## Principle 5 - Explicit Boundaries

Each component should have a clear responsibility and interface.

## Principle 6 - Replaceable Providers

Models and infrastructure providers should be replaceable where practical.

## Principle 7 - Observable Behavior

Important system behavior should be measurable.

## Principle 8 - Secure Defaults

If a security decision cannot be established, the system should deny the operation.

---

# 19. Related Documentation

- `architecture/backend.md`
- `architecture/frontend.md`
- `architecture/rag.md`
- `architecture/data-model.md`
- `architecture/integrations.md`
- `security/security-architecture.md`
- `security/authentication.md`
- `security/authorization.md`
- `security/prompt-injection.md`
- `security/threat-model.md`
- `rag/ingestion.md`
- `rag/retrieval.md`
- `rag/embeddings.md`
- `rag/generation.md`
- `rag/evaluation.md`
- `development/phases.md`
- `development/progress.md`
- `deployment/local-development.md`
- `deployment/docker.md`
- `deployment/production.md`
