# Backend Architecture

## 1. Purpose

This document defines the FastAPI backend architecture for the Supabase-based Private Enterprise AI Platform.

The backend is responsible for HTTP/API handling, Supabase JWT validation, application authorization, business logic, document ingestion, RAG orchestration, audit logging, security controls, and integrations with Supabase, Qdrant Cloud, and Ollama.

Supabase provides authentication, PostgreSQL, and object storage. FastAPI remains the business-logic and authorization layer.

---

# 2. Architecture

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

The architecture should prevent:

- Business logic inside route handlers
- Direct infrastructure access from API routes
- Direct LLM calls from API routes
- Authorization logic scattered across the application
- RAG components bypassing security controls
- Treating Supabase Auth as application authorization

---

# 3. Backend Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── documents.py
│   │   ├── users.py
│   │   └── admin.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── rag/
│   ├── agents/
│   ├── security/
│   └── integrations/
│       ├── supabase/
│       │   └── client.py
│       ├── qdrant.py
│       ├── ollama.py
│       └── storage.py
└── tests/
```

The existing module layout remains useful. Supabase-specific details belong in integration adapters, configuration, and identity services, not in API handlers.

---

# 4. API Layer

`app/api/` contains thin route definitions.

Responsibilities:

- Define endpoints
- Validate request schemas
- Resolve authentication dependencies
- Call application services
- Return response schemas
- Translate known application errors into HTTP responses

Routes must not calculate permissions, directly retrieve from Qdrant Cloud, or call Ollama.

---

# 5. Authentication and Identity

Supabase Auth handles:

- User authentication
- Password management
- Session management
- JWT issuance
- Token refresh
- Authentication lifecycle

FastAPI does not implement custom password verification or primary login credentials.

```text
Registration/Login
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
AuthenticatedUser
       ↓
public.profiles lookup
       ↓
AuthorizationService
```

Authentication answers "Who are you?"

Authorization answers "What are you allowed to access?"

---

# 6. Application Services

`app/services/` contains application-level business operations:

- Profile and user administration
- Document management
- Permission resolution
- Audit events
- RAG orchestration
- Supabase Storage lifecycle coordination

Services should not depend directly on HTTP concepts. They should receive an application identity and explicit inputs, perform authorization, and call domain/infrastructure abstractions.

---

# 7. Authorization

Authorization is centralized in the permission service and RAG authorization modules.

Responsibilities:

- Determine user roles
- Determine user permissions
- Enforce route-level permission checks
- Later: determine department membership
- Later: resolve document permissions
- Later: evaluate classification restrictions
- Later: produce trusted retrieval filters for Qdrant Cloud

```text
PermissionService
    ├── has_role()
    ├── has_permission()
    ├── get_user_roles()
    └── get_user_permissions()
```

Client-supplied authorization filters are never trusted.

---

# 8. Database Layer

`app/db/` manages database connectivity when direct PostgreSQL access is used.

Supabase PostgreSQL is the database provider. Supabase-managed authentication records live in `auth.users`. Application data lives in `public`.

Responsibilities:

- Database engine configuration
- Session management
- Migration integration
- Transaction boundaries
- Controlled database access for services

SQLAlchemy and Alembic may be used for application tables. Supabase migrations may also be used if selected as the project migration workflow.

---

# 9. Models and Schemas

Models represent application-managed persistent entities:

```text
Profile
Role
Department
Document
Permission
AuditLog
```

Do not model Supabase-managed password data in application tables. `auth.users` is linked to `public.profiles`.

Schemas define API contracts and remain separate from database models so internal fields do not accidentally become public API fields.

---

# 10. Core and Security Layers

`app/core/` contains centralized configuration, JWT validation helpers, logging, and exceptions.

`app/security/` contains prompt-injection defenses, input validation, document security checks, rate limiting, and security-specific validation.

`core/security.py` must not become a custom password authentication system.

---

# 11. RAG Layer

The RAG layer contains:

```text
ingestion/
embeddings/
retrieval/
authorization/
generation/
pipelines/
```

The secure RAG entry point is:

```text
Chat Service
      ↓
Secure RAG Pipeline
      ↓
Authorization
      ↓
Permission-Aware Retrieval
      ↓
Context Validation
      ↓
Generation
      ↓
Citations
```

The RAG layer must receive trusted authorization constraints before retrieving protected chunks.

---

# 12. Integrations Layer

`app/integrations/` isolates infrastructure clients:

- Supabase Auth/PostgreSQL/Storage
- Qdrant Cloud
- Ollama
- Local embedding providers

This layer configures clients, translates provider errors, handles timeouts, and keeps service-role credentials server-side.

The Supabase integration exposes separate client creation paths for user-scoped
access and explicitly privileged service access. Service-role access must be
requested intentionally and must not be used as a shortcut around application
authorization. Missing configuration and provider failures are translated into
application exceptions so raw provider errors do not leak through API responses.

---

# 13. Supabase Keys

The frontend may use the public Supabase URL and publishable key.

The Supabase service-role or secret key must never be exposed to:

- Browser
- Next.js client-side code
- Public API responses
- Git
- Logs
- Frontend environment variables

FastAPI may use privileged Supabase credentials for trusted server-side operations when required.

The backend configuration includes:

```env
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
```

`SUPABASE_URL` is not secret. `SUPABASE_PUBLISHABLE_KEY` is public but still
validated by configuration. `SUPABASE_SECRET_KEY` is highly privileged and must
remain backend-only.

Module 4 uses the service client deliberately for backend RBAC/profile lookups because RBAC tables are not writable or broadly readable by ordinary users. This does not replace application authorization; route dependencies still authenticate the request and enforce permissions before protected handlers proceed.

---

# 14. Request Lifecycle

```text
HTTP Request
     ↓
FastAPI Router
     ↓
Request Validation
     ↓
get_current_user()
     ↓
Supabase Auth JWT Validation
     ↓
AuthenticatedUser
     ↓
require_permission()
     ↓
AuthorizationService
     ↓
Application Service
     ↓
Authorization
     ↓
Domain Operation
     ↓
Infrastructure
     ↓
Response Schema
     ↓
HTTP Response
```

---

# 15. Chat Request Lifecycle

```text
HTTP Request
      ↓
Chat Router
      ↓
Request Validation
      ↓
Supabase JWT Validation
      ↓
Identity Resolution
      ↓
Chat Service
      ↓
Secure RAG Pipeline
      ├── Query Analysis
      ├── Authorization
      ├── Permission Filter
      ├── Retrieval
      ├── Reranking
      ├── Context Validation
      ├── LLM Generation
      └── Citation Validation
      ↓
Audit Service
      ↓
Response Schema
```

---

# 16. Document Upload Lifecycle

```text
HTTP Upload
     ↓
Document Router
     ↓
Input Validation
     ↓
Supabase JWT Validation
     ↓
Authorization
     ↓
Document Service
     ↓
Supabase Storage
     ↓
File Security
     ↓
Ingestion Pipeline
     ├── Load
     ├── Extract
     ├── Clean
     ├── Chunk
     └── Metadata
     ↓
Supabase PostgreSQL Metadata
     ↓
Embedding Provider
     ↓
Qdrant Cloud
     ↓
Audit Event
```

---

# 17. Error Handling and Auditing

Errors should use explicit application exception types:

```text
AuthenticationError
AuthorizationError
ValidationError
ResourceNotFoundError
ConflictError
IngestionError
RetrievalError
GenerationError
InfrastructureError
```

Security-sensitive errors fail closed.

Authentication failures use `AuthenticationError` and return `401` through the
global error handlers. Missing or malformed `Authorization` headers and invalid,
expired, or untrusted tokens do not reach protected route logic.

Routes and services should raise application exceptions rather than building
HTTP error responses directly. FastAPI global exception handlers translate
application exceptions, request validation errors, framework HTTP errors, and
unexpected exceptions into a consistent response envelope:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "The requested resource was not found.",
    "request_id": "..."
  }
}
```

Unexpected exceptions are logged server-side and returned to clients as a
generic internal error. Error responses must not expose stack traces, provider
errors, filesystem paths, secrets, tokens, or implementation details. Each
request receives an `X-Request-ID` value for correlation.

Audit events are written through a dedicated audit service to Supabase PostgreSQL and must avoid passwords, tokens, secrets, full confidential documents, and unnecessary prompt contents.

---

# 18. Backend Non-Goals

The backend should not:

- Implement custom password authentication
- Store password credentials in application profiles
- Treat Supabase Auth as application authorization
- Treat the LLM as a security component
- Allow direct frontend access to Qdrant Cloud or Ollama
- Duplicate authorization logic in every endpoint
- Couple the whole application to one AI provider

---

# 19. Definition of Done

- [ ] API routes are thin and separated by domain
- [ ] Supabase JWT validation is centralized
- [ ] Application identity resolves through `public.profiles`
- [ ] Application services contain business orchestration
- [ ] Authorization is centralized
- [ ] RAG is modular
- [ ] AI providers use abstractions
- [ ] Infrastructure clients are isolated
- [ ] Service-role credentials never reach the frontend
- [ ] Audit logging is centralized
- [ ] Unauthorized context cannot reach the LLM

---

# 20. Related Documentation

- `architecture/system.md`
- `architecture/data-model.md`
- `architecture/integrations.md`
- `security/authentication.md`
- `security/authorization.md`
- `rag/ingestion.md`
- `development/phases.md`
