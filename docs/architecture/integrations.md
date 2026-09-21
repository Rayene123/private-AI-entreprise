# Integration Architecture

## 1. Purpose

This document defines the integration boundaries between the Private Enterprise AI Platform and its infrastructure providers.

The platform integrates with:

- Supabase Auth
- Supabase PostgreSQL
- Supabase Storage
- Qdrant Cloud
- Ollama

The goal is to keep infrastructure concerns isolated from application and domain logic.

The backend must remain modular so that infrastructure providers can be replaced without rewriting the core application.

---

# 2. Integration Architecture

The platform uses the following architecture:

```text
                         ┌─────────────────┐
                         │    Next.js      │
                         │    Frontend     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  Supabase Auth  │
                         │                 │
                         │ Identity / JWT  │
                         └────────┬────────┘
                                  │
                                  │ JWT
                                  ▼
                         ┌─────────────────┐
                         │     FastAPI     │
                         │                 │
                         │ API             │
                         │ Services        │
                         │ Authorization   │
                         │ RAG             │
                         └───┬────┬────┬───┘
                             │    │    │
                ┌────────────┘    │    └────────────┐
                ▼                 ▼                 ▼
       ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
       │    Supabase    │ │    Qdrant Cloud    │ │    Ollama    │
       │                │ │              │ │              │
       │ PostgreSQL     │ │ Vector DB    │ │ Local LLM    │
       │ Storage        │ │              │ │              │
       └────────────────┘ └──────────────┘ └──────────────┘
```

Supabase itself is composed of multiple services built around a PostgreSQL database, including Auth and Storage.

---

# 3. Integration Principles

## 3.1 Separation of concerns

Each external service has a specific responsibility.

| Service             | Responsibility                      |
| ------------------- | ----------------------------------- |
| Supabase Auth       | Authentication and identity         |
| Supabase PostgreSQL | Authoritative relational data       |
| Supabase Storage    | Original document files             |
| Qdrant Cloud              | Vector retrieval                    |
| Ollama              | Local LLM inference                 |
| FastAPI             | Application logic and orchestration |

No external provider should become responsible for unrelated application concerns.

---

## 3.2 Provider abstraction

Application services should depend on interfaces rather than concrete infrastructure implementations wherever practical.

Conceptually:

```text
LLMProvider
    └── OllamaProvider

EmbeddingProvider
    └── SentenceTransformerProvider

VectorStore
    └── QdrantVectorStore

ObjectStorage
    └── SupabaseStorage

IdentityProvider
    └── SupabaseIdentityProvider
```

Concrete implementations belong under:

```text
backend/app/integrations/
```

The domain and service layers should not contain provider-specific implementation details.

---

# 4. Supabase

Supabase provides three major capabilities used by the platform:

```text
Supabase
├── Auth
├── PostgreSQL
└── Storage
```

These should be treated as separate integration boundaries even though they belong to the same platform.

---

# 5. Supabase Auth

## Responsibility

Supabase Auth is responsible for:

- User authentication
- Password management
- Session management
- JWT issuance
- JWT refresh
- Authentication lifecycle

Supabase Auth uses JWTs and provides the authentication service responsible for validating, issuing, and refreshing tokens.

The application must not implement a second password authentication system.

---

## 5.1 Authentication Flow

```text
User
  │
  ▼
Next.js
  │
  ▼
Supabase Auth
  │
  │ JWT
  ▼
Next.js
  │
  │ Authorization header
  ▼
FastAPI
  │
  ▼
JWT validation
  │
  ▼
Supabase user ID
  │
  ▼
Application profile
  │
  ▼
Application identity
```

The Supabase Auth user is the source of identity.

The application's `profiles` table contains additional business/application information.

---

# 6. Authentication vs Authorization

Authentication and authorization are separate responsibilities.

## Authentication

Authentication answers:

> Who is this user?

Primary provider:

```text
Supabase Auth
```

## Authorization

Authorization answers:

> What is this user allowed to access?

Primary application layer:

```text
FastAPI Authorization Service
```

Additional database protection:

```text
Supabase PostgreSQL RLS
```

RAG protection:

```text
Qdrant Cloud permission filters
```

Therefore:

```text
Supabase Auth
      ↓
Identity
      ↓
FastAPI Authorization
      ↓
Permission-aware Retrieval
      ↓
Generation
```

The LLM never determines authorization.

---

# 7. Supabase PostgreSQL

Supabase provides a full PostgreSQL database rather than a proprietary database abstraction. PostgreSQL is the authoritative relational data store for the application.

Application-managed tables include:

```text
public.profiles
public.departments
public.roles
public.permissions
public.user_roles
public.role_permissions
public.documents
public.document_permissions
public.document_chunks
public.audit_logs
```

Supabase Auth manages authentication-related data under:

```text
auth.users
```

The application should reference the Auth user from its own `profiles` table rather than duplicating authentication credentials.

---

# 8. PostgreSQL as Source of Truth

PostgreSQL is authoritative for:

- Users' application profiles
- Departments
- Roles
- Permissions
- Document metadata
- Document permissions
- Document chunks
- Audit records
- Ingestion state

Qdrant Cloud is not authoritative for these entities.

The relationship is:

```text
Supabase PostgreSQL
        │
        │ authoritative state
        ▼
      Qdrant Cloud
        │
        │ derived retrieval index
        ▼
    Retrieval
```

If Qdrant Cloud is lost, the vector index should be rebuildable from the authoritative application state.

---

# 9. PostgreSQL Access

FastAPI is the primary backend for application operations.

Conceptually:

```text
API
 ↓
Service
 ↓
Repository / Data Access
 ↓
SQLAlchemy
 ↓
Supabase PostgreSQL
```

API routes should not contain raw database operations.

Database access should be centralized through appropriate repositories or service-level data access abstractions.

---

# 10. Database Connection Management

The exact PostgreSQL connection method will depend on the deployment environment.

The backend must support:

- Environment-based connection configuration
- Connection pooling
- Connection timeouts
- Transaction management
- Safe credential handling

Supabase provides multiple PostgreSQL connection options, including direct connections and connection pooler modes. The appropriate mode should be selected during implementation according to the deployment environment and connection pattern.

Database credentials must never be hard-coded.

---

# 11. Supabase Row Level Security

Row Level Security is part of the database security architecture.

Supabase recommends RLS for protecting tables exposed through its Data APIs. RLS policies act as database-level authorization rules, while PostgreSQL grants determine whether a role can access an object at all.

The platform should therefore use:

```text
FastAPI Authorization
        +
Supabase RLS
```

as defense in depth.

---

# 12. RLS Is Not the RAG Authorization Boundary

RLS does not replace the application's RAG authorization logic.

The RAG pipeline must explicitly perform:

```text
Authenticated User
       ↓
Identity Resolution
       ↓
Authorization Policy
       ↓
Permission Filter
       ↓
Qdrant Cloud Retrieval
       ↓
Authorized Context
       ↓
LLM
```

The platform must never:

```text
Retrieve all documents
        ↓
Send everything to LLM
        ↓
Ask LLM not to reveal unauthorized information
```

That architecture is insecure.

---

# 13. Supabase Service Role

Supabase provides elevated server-side credentials that can bypass RLS.

The service-role credential must therefore be treated as a highly privileged secret.

It must never be exposed to:

- Browser code
- Client-side JavaScript
- Next.js public environment variables
- API responses
- Git
- Logs
- Error messages

Supabase explicitly documents that the `service_role` role bypasses RLS and should therefore remain server-side.

---

# 14. Supabase Storage

Supabase Storage is responsible for storing original uploaded enterprise documents.

The architecture is:

```text
User
 ↓
FastAPI
 ↓
Authorization
 ↓
Supabase Storage
 ↓
Original File
```

PostgreSQL stores the application's document metadata.

The binary object remains in Storage.

---

# 15. Storage Bucket

The initial enterprise document bucket should be private:

```text
documents
```

Conceptual object structure:

```text
documents/
    {document_id}/
        {version}/
            original_filename
```

The exact path-generation strategy will be defined during implementation.

Object paths must not be treated as authorization mechanisms.

---

# 16. Storage Security

Enterprise documents must not be publicly accessible.

Storage access should use:

- Private buckets
- RLS policies
- Application authorization
- File validation
- Size limits
- MIME validation
- Controlled object paths

Supabase Storage uses a dedicated `storage` schema and RLS-based access control. Storage metadata should be treated as provider-managed and operations such as upload, move, copy, and delete should go through the Storage API rather than directly modifying Storage tables.

---

# 17. Document Upload Flow

```text
User
 ↓
Next.js
 ↓
FastAPI
 ↓
Authentication
 ↓
Authorization
 ↓
File Validation
 ↓
Supabase Storage
 ↓
Document Metadata
 ↓
Ingestion Pipeline
```

The system must validate authorization before accepting an operation that creates or modifies an enterprise document.

---

# 18. Document Download Flow

For protected documents:

```text
User
 ↓
Next.js
 ↓
FastAPI
 ↓
Authentication
 ↓
Authorization
 ↓
Supabase Storage
 ↓
Authorized File
```

If signed URLs are introduced later, they must only be generated after authorization has succeeded.

A storage URL must never be treated as proof that the requesting user is authorized.

---

# 19. Storage Failure Behavior

If Storage is unavailable:

```text
Upload
 ↓
Storage unavailable
 ↓
Upload fails
 ↓
Document is not marked as successfully indexed
```

The database must not incorrectly report a successfully stored document when the object does not exist.

Ingestion state must represent the actual state of the process.

---

# 20. Qdrant Cloud

Qdrant Cloud is the vector database used for semantic retrieval.

It stores:

- Embedding vectors
- Chunk identifiers
- Document identifiers
- Retrieval metadata
- Authorization-relevant metadata

Qdrant Cloud is a retrieval system, not the application's source of truth.

---

# 21. Qdrant Cloud Data Flow

### Indexing

```text
Document
 ↓
Chunk
 ↓
Embedding
 ↓
Qdrant Cloud
```

### Retrieval

```text
User Query
 ↓
FastAPI
 ↓
Authorization
 ↓
Permission Filter
 ↓
Qdrant Cloud
 ↓
Authorized Results
```

Authorization must be resolved before retrieval.

---

# 22. Qdrant Cloud Payload

Each vector should contain enough metadata to support filtering.

Minimum conceptual payload:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "department_id": "...",
  "classification": "INTERNAL"
}
```

Additional metadata may include:

```json
{
  "chunk_index": 5,
  "document_version": 1,
  "page_number": 7
}
```

Do not store unnecessary sensitive document content in Qdrant Cloud metadata.

---

# 23. Qdrant Cloud Authorization

FastAPI generates retrieval filters from trusted application state.

The user must not directly control authorization filters.

Unsafe:

```text
User
 ↓
department_id = "finance"
 ↓
Qdrant Cloud
```

Safe:

```text
User JWT
 ↓
FastAPI identity
 ↓
Database permissions
 ↓
Authorization policy
 ↓
Server-generated Qdrant Cloud filter
 ↓
Qdrant Cloud
```

---

# 24. Qdrant Cloud Failure Behavior

If Qdrant Cloud is unavailable:

```text
Retrieval
 ↓
Qdrant Cloud unavailable
 ↓
Controlled failure
```

The system must not:

- Fabricate retrieved documents
- Pretend retrieval succeeded
- Bypass authorization
- Send unauthorized fallback content to the LLM

A controlled error or temporary RAG unavailability is preferable to an unsafe response.

---

# 25. Ollama

Ollama provides local LLM inference.

The application should interact with Ollama through an abstraction:

```text
GenerationService
        ↓
LLMProvider
        ↓
OllamaProvider
        ↓
Ollama
        ↓
Local Model
```

Application code should depend on `LLMProvider`, not directly on Ollama APIs.

---

# 26. Ollama Responsibilities

Ollama is responsible for:

- Loading models
- Running local inference
- Generating responses
- Streaming responses where supported

FastAPI remains responsible for:

- Prompt construction
- Context construction
- Authorization
- Grounding rules
- Citation handling
- Output validation
- Timeout handling
- Error handling

Ollama must never determine whether a document is authorized.

---

# 27. Ollama Failure Behavior

If Ollama is unavailable:

```text
Generation Request
 ↓
Ollama unavailable
 ↓
Controlled error
```

The system must not fabricate an LLM response.

It must not silently switch to another provider unless an explicitly configured fallback provider exists.

---

# 28. End-to-End RAG Integration

The complete request flow is:

```text
                         User
                           │
                           ▼
                        Next.js
                           │
                           ▼
                    Supabase Auth
                           │
                           │ JWT
                           ▼
                        FastAPI
                           │
                           ▼
                 Identity Resolution
                           │
                           ▼
                     Authorization
                           │
                           ▼
                Query Validation
                           │
                           ▼
             Permission-Aware Retrieval
                           │
                           ▼
                         Qdrant Cloud
                           │
                           ▼
                  Authorized Chunks
                           │
                           ▼
                    Context Builder
                           │
                           ▼
                         Ollama
                           │
                           ▼
                  Output Validation
                           │
                           ▼
                       Citations
                           │
                           ▼
                        Response
```

The critical boundary is:

```text
Authorization
      ↓
Retrieval
      ↓
Generation
```

Never:

```text
Retrieval
      ↓
Authorization
```

---

# 29. Document Ingestion Integration

The ingestion architecture is:

```text
                     Upload
                        │
                        ▼
                     FastAPI
                        │
                        ▼
                  Authorization
                        │
                        ▼
                Supabase Storage
                        │
                        ▼
                 File Validation
                        │
                        ▼
                    Extraction
                        │
                        ▼
                     Cleaning
                        │
                        ▼
                     Chunking
                        │
                        ▼
              PostgreSQL Metadata
                        │
                        ▼
                    Embeddings
                        │
                        ▼
                     Qdrant Cloud
```

Document state should distinguish between:

```text
PENDING
PROCESSING
INDEXED
FAILED
```

A document must not become retrievable before its ingestion process has successfully completed.

---

# 30. Consistency Across Services

Supabase PostgreSQL, Supabase Storage, Qdrant Cloud, and Ollama do not participate in one shared transaction.

Therefore:

```text
PostgreSQL transaction
        ≠
Storage transaction
        ≠
Qdrant Cloud transaction
        ≠
LLM transaction
```

The ingestion system must explicitly manage state and failure recovery.

Example:

```text
PENDING
   ↓
PROCESSING
   ↓
INDEXED
```

Failure:

```text
PROCESSING
   ↓
FAILED
```

The system must be able to retry failed ingestion safely.

---

# 31. Error Handling

Infrastructure errors should be translated into application-level errors.

Examples:

```text
IntegrationUnavailable
IntegrationTimeout
IntegrationAuthenticationError
IntegrationAuthorizationError
IntegrationValidationError
IntegrationRateLimited
IntegrationDataError
```

Raw provider exceptions should not be returned directly to clients.

Error responses should avoid revealing:

- Credentials
- Connection strings
- Internal hostnames
- Provider internals
- Stack traces
- Sensitive document information

---

# 32. Timeouts

Every network integration must have an explicit timeout.

At minimum:

```text
Supabase Auth
Supabase Storage
PostgreSQL
Qdrant Cloud
Ollama
```

Timeout values must be configuration-driven.

A request must never wait indefinitely for an external service.

---

# 33. Retry Policy

Retries should only be used for transient failures.

Potential retryable failures:

```text
Temporary network failure
Timeout
Temporary service unavailable
```

Do not blindly retry:

```text
Invalid credentials
Authorization failure
Permission denied
Invalid request
Validation failure
Malformed data
```

Every retry policy must have:

- Maximum attempts
- Backoff
- Maximum delay
- Clear failure behavior

---

# 34. Observability

Integration metrics should include:

```text
Request count
Success count
Failure count
Latency
Timeout count
Retry count
```

Use correlation/request IDs to connect events across services.

Logs must not contain:

- Passwords
- JWTs
- Supabase service-role keys
- API keys
- Full confidential documents
- Unnecessary sensitive prompts
- Raw provider credentials

---

# 35. Configuration

Configuration must be environment-driven.

Conceptual configuration:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

DATABASE_URL=

QDRANT_URL=
QDRANT_API_KEY=

OLLAMA_HOST=
OLLAMA_MODEL=
```

The exact variables may evolve during implementation.

Never commit real values.

Never hard-code secrets.

---

# 36. Local Development Architecture

The default local development architecture is:

```text
Docker
├── FastAPI
├── Next.js
├── Qdrant Cloud
└── Ollama

External
└── Supabase
    ├── Auth
    ├── PostgreSQL
    └── Storage
```

A local PostgreSQL container is not part of the default architecture.

A fully self-hosted Supabase deployment may be introduced later, but it is not required for the initial development environment.

---

# 37. Testing Strategy

Each integration must be independently testable.

## Supabase Auth

Test:

- Valid JWT
- Expired JWT
- Invalid JWT
- Missing JWT
- Unknown user
- Inactive user

## PostgreSQL

Test:

- CRUD operations
- Foreign-key constraints
- Unique constraints
- Transactions
- Permission queries
- RLS policies

## Storage

Test:

- Upload
- Download
- Unauthorized access
- Invalid file
- Oversized file
- Deletion authorization

## Qdrant Cloud

Test:

- Collection creation
- Vector indexing
- Retrieval
- Metadata filtering
- Empty results
- Service failure

## Ollama

Test:

- Generation
- Timeout
- Model unavailable
- Invalid response
- Service failure

Unit tests should use mocks/fakes where appropriate.

Integration tests should use real infrastructure for critical integration paths.

---

# 38. Provider Replacement

The platform must remain replaceable at the infrastructure boundary.

## LLM

```text
LLMProvider
├── OllamaProvider
└── FutureCloudProvider
```

## Vector Store

```text
VectorStore
├── QdrantVectorStore
└── FutureVectorStore
```

## Object Storage

```text
ObjectStorage
├── SupabaseStorage
└── FutureS3Storage
```

## Identity

```text
IdentityProvider
├── SupabaseIdentityProvider
└── FutureIdentityProvider
```

Replacing an infrastructure provider should not require rewriting the domain layer.

---

# 39. Security Invariants

The following invariants are mandatory:

1. Supabase Auth establishes user identity.
2. FastAPI establishes application authorization.
3. Supabase RLS provides database-level defense in depth.
4. Service-role credentials remain server-side.
5. Qdrant Cloud is never the authoritative authorization source.
6. Authorization is performed before RAG retrieval.
7. Unauthorized chunks never reach the LLM.
8. Enterprise documents are stored in private Storage buckets.
9. Signed URLs, if introduced, are generated only after authorization.
10. Provider failures fail safely.
11. Secrets are never written to logs.
12. Provider implementations remain behind appropriate abstractions.
13. Missing authorization information results in denial.
14. Qdrant Cloud can be rebuilt from authoritative application state.

---

# 40. Integration Boundaries

The final responsibility boundaries are:

```text
┌─────────────────────────────────────────────────────┐
│                     Next.js                         │
│                                                     │
│ UI / User Interaction / Client Session              │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                 Supabase Auth                       │
│                                                     │
│ Identity / Authentication / JWT                     │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                    FastAPI                          │
│                                                     │
│ API / Business Logic / Authorization / RAG          │
└──────────────┬──────────────┬──────────────┬────────┘
               │              │              │
               ▼              ▼              ▼
        ┌────────────┐ ┌────────────┐ ┌────────────┐
        │  Supabase  │ │   Qdrant Cloud   │ │   Ollama   │
        │ PostgreSQL │ │            │ │            │
        │ + Storage  │ │ Retrieval  │ │ Generation │
        └────────────┘ └────────────┘ └────────────┘
```

The core business and security logic remains inside FastAPI.

---

# 41. Definition of Done

This integration architecture is complete when:

- [x] Supabase Auth responsibility is defined
- [x] Supabase PostgreSQL responsibility is defined
- [x] Supabase Storage responsibility is defined
- [x] Qdrant Cloud responsibility is defined
- [x] Ollama responsibility is defined
- [x] Provider abstraction strategy is defined
- [x] Authentication/authorization boundary is explicit
- [x] RLS role is defined
- [x] Service-role security boundary is defined
- [x] Storage security is defined
- [x] Qdrant Cloud authorization model is defined
- [x] PostgreSQL/Qdrant Cloud source-of-truth boundary is defined
- [x] Failure behavior is defined
- [x] Timeout behavior is defined
- [x] Retry behavior is defined
- [x] Configuration strategy is defined
- [x] Local development architecture is defined
- [x] Testing strategy is defined
- [x] Provider replacement strategy is defined
- [x] Security invariants are defined

---

# 42. Related Documents

This document is related to:

```text
docs/architecture/system.md
docs/architecture/backend.md
docs/architecture/data-model.md

docs/security/authentication.md
docs/security/authorization.md
docs/security/security-architecture.md
docs/security/threat-model.md

docs/rag/ingestion.md
docs/rag/retrieval.md
docs/rag/embeddings.md
docs/rag/generation.md

docs/deployment/local-development.md
docs/deployment/docker.md

docs/development/phases.md
docs/development/testing-strategy.md
```
# Integration Contracts

## 1. Purpose

This document defines how FastAPI, Next.js, Supabase, Qdrant Cloud, and Ollama interact.

Supabase provides Auth, PostgreSQL, and Storage. Qdrant Cloud remains the vector database. Ollama remains the local LLM provider. FastAPI remains the business-logic and authorization layer.

---

# 2. Supabase Auth

Supabase Auth owns:

- Registration and login
- Password management
- Session management
- Token refresh
- JWT issuance
- Authentication lifecycle

Flow:

```text
Next.js
  ↓
Supabase Auth
  ↓
JWT
  ↓
FastAPI
  ↓
JWT validation
  ↓
Supabase user ID
  ↓
public.profiles lookup
```

FastAPI validates the JWT and resolves the application profile. Supabase Auth answers who the user is. FastAPI authorization answers what the user may access.

The browser may receive only public Supabase configuration. Service-role credentials are server-side only.

---

# 3. Supabase PostgreSQL

Supabase PostgreSQL is the authoritative relational store for application metadata.

It stores:

- Profiles
- Departments
- Roles
- Permissions
- Documents
- Document permissions
- Document chunks
- Audit logs

SQLAlchemy may be used for direct database access. Migrations may use Supabase migrations or Alembic, but the selected workflow must be versioned and reviewable.

Transactions must preserve consistency across document metadata, chunk metadata, and ingestion status. If a later step fails, the system must not mark a document as successfully indexed.

RLS should be enabled on appropriate exposed tables. RLS is defense in depth and does not replace FastAPI authorization.

---

# 4. Supabase Storage

Supabase Storage is the primary object store for uploaded enterprise documents.

Document flow:

```text
Upload
 ↓
Supabase Storage object
 ↓
FastAPI ingestion
 ↓
PostgreSQL metadata
 ↓
Qdrant Cloud index
```

Object paths should be generated by trusted server-side logic. They should avoid leaking unnecessary business meaning and should support document versioning or replacement.

Access control is enforced by FastAPI authorization and Supabase Storage/RLS policies where applicable.

---

# 5. Qdrant Cloud

Qdrant Cloud stores embedding vectors and retrieval payload metadata. It is not the source of truth for authorization.

Payloads should include enough metadata for server-derived retrieval filters:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "department_id": "...",
  "classification": "INTERNAL"
}
```

FastAPI builds Qdrant Cloud filters from trusted profile, role, department, document permission, and classification policy data. Clients must not construct authorization filters.

If Qdrant Cloud is lost, it must be rebuildable from Supabase PostgreSQL metadata and Supabase Storage source documents.

---

# 6. Ollama

Ollama provides local LLM inference behind an `LLMProvider` abstraction.

FastAPI sends only authorized context to Ollama.

The request boundary should define:

- Model name
- Prompt/template
- Authorized context
- Generation parameters
- Timeouts
- Failure handling

Ollama failures must not expose unauthorized data or partial internal prompts.

---

# 7. Required Environment

Expected variables include:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_URL=
QDRANT_URL=
QDRANT_API_KEY=
OLLAMA_BASE_URL=
```

Never commit real secrets.
