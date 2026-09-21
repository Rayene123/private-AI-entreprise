# Security Architecture

## 1. Purpose

This document defines the security architecture of the Private Enterprise AI Platform.

The objective is to ensure that security is enforced as an architectural property rather than as a collection of isolated features.

The platform handles potentially confidential enterprise documents and allows users to query those documents through an AI/RAG system. Therefore, security controls must protect:

- User identities
- Authentication sessions
- Enterprise documents
- Document metadata
- Document embeddings
- Retrieval results
- Conversations
- Generated responses
- Administrative operations
- Secrets and credentials
- Audit records
- AI model and tool execution

The architecture follows:

- Defense in depth
- Least privilege
- Deny by default
- Secure by default
- Separation of concerns
- Fail-secure behavior
- Zero-trust principles
- Explicit trust boundaries
- Centralized authorization
- Security through the entire RAG lifecycle

Security architecture is defined during design and must evolve when components, interfaces, roles, data flows, or trust relationships change.

---

# 2. Scope

This architecture covers:

- Next.js frontend
- Supabase Auth
- Supabase PostgreSQL
- Supabase Storage
- FastAPI backend
- Qdrant Cloud
- Ollama
- LangGraph
- RAG ingestion
- RAG retrieval
- LLM generation
- RBAC
- Document authorization
- Prompt-injection defenses
- API security
- Secrets management
- Audit logging
- Rate limiting
- Docker runtime security
- Backup and recovery
- Security testing

This document does not replace:

- `docs/security/authentication.md`
- `docs/security/authorization.md`
- `docs/security/prompt-injection.md`
- `docs/security/threat-model.md`

Those documents contain detailed requirements for their respective areas.

---

# 3. Security Architecture Principles

## 3.1 Defense in Depth

No single security mechanism should be treated as sufficient protection.

For example, document confidentiality should not depend exclusively on:

- Frontend UI restrictions
- PostgreSQL RLS
- FastAPI authorization
- Qdrant Cloud filters
- LLM prompts

Instead, multiple layers must work together.

Example:

```text
User
  │
  ▼
Supabase Authentication
  │
  ▼
FastAPI Authentication
  │
  ▼
Application Authorization
  │
  ▼
Permission-Aware Retrieval
  │
  ▼
Qdrant Cloud Authorization Filter
  │
  ▼
Authorized Context
  │
  ▼
LLM
  │
  ▼
Output Validation
```

If one layer fails, another layer should limit the resulting impact.

Defense in depth is a core secure-product-design principle.

---

# 4. High-Level Security Architecture

```text
                         ┌──────────────────────┐
                         │       User           │
                         └──────────┬───────────┘
                                    │
                              HTTPS / Auth
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Next.js Frontend   │
                         │                      │
                         │ UI authorization     │
                         │ Input validation     │
                         │ Secure session use   │
                         └──────────┬───────────┘
                                    │
                                  JWT
                                    │
                                    ▼
                  ┌────────────────────────────────┐
                  │          FastAPI API            │
                  │                                │
                  │ Authentication                 │
                  │ Authorization                  │
                  │ Input validation                │
                  │ Rate limiting                   │
                  │ Business logic                  │
                  │ Audit logging                   │
                  └───────────────┬────────────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
              ▼                   ▼                    ▼
      ┌──────────────┐   ┌────────────────┐   ┌───────────────┐
      │   Supabase   │   │      RAG       │   │     Audit     │
      │ PostgreSQL   │   │    Pipeline    │   │    Logging    │
      │              │   │                │   │               │
      │ Users        │   │ Authorization  │   │ Security      │
      │ Roles        │   │ Retrieval      │   │ Events        │
      │ Permissions  │   │ Validation     │   │ Admin Events  │
      │ Documents    │   └───────┬────────┘   └───────────────┘
      └──────┬───────┘           │
             │                   ▼
             │           ┌───────────────┐
             │           │    Qdrant Cloud     │
             │           │               │
             │           │ Vector Index  │
             │           │ Permission    │
             │           │ Metadata      │
             │           └───────┬───────┘
             │                   │
             │ Authorized        │
             │ Context           │
             │                   ▼
             │           ┌───────────────┐
             │           │    Ollama     │
             │           │               │
             │           │ Local LLM     │
             │           └───────┬───────┘
             │                   │
             ▼                   ▼
      ┌───────────────┐   ┌───────────────┐
      │   Supabase    │   │    Response   │
      │    Storage    │   │   Validation  │
      │               │   └───────────────┘
      │ Original Docs │
      └───────────────┘
```

---

# 5. Trust Boundaries

The platform is divided into explicit trust zones.

## Zone 0 — External / Untrusted

Includes:

- Unauthenticated users
- Internet traffic
- Uploaded documents
- User prompts
- Retrieved external content
- Potentially malicious document content

No content originating from this zone should automatically be trusted.

---

## Zone 1 — Authenticated Client

Includes:

- Next.js application
- Authenticated browser session
- User-generated requests

The frontend is not a trusted authorization boundary.

A malicious user can bypass the frontend and call the backend directly.

Therefore:

```text
Frontend authorization ≠ Security authorization
```

---

## Zone 2 — Application Security Boundary

The FastAPI backend is the primary application security boundary.

Responsibilities include:

- JWT validation
- Identity resolution
- Authorization
- Input validation
- Rate limiting
- Business rules
- Permission-aware retrieval
- Audit logging
- Output validation

All sensitive operations must pass through this boundary.

---

## Zone 3 — Protected Data Services

Includes:

- Supabase PostgreSQL
- Supabase Storage
- Qdrant Cloud

These systems contain protected enterprise information.

PostgreSQL is the authoritative relational source.

Qdrant Cloud is a derived retrieval index.

Supabase Storage contains original enterprise documents.

---

## Zone 4 — Model Execution

Includes:

- Ollama
- LangGraph
- Future tools/agents

The model execution environment must receive only information that the application has already authorized.

The LLM must never be responsible for deciding whether a user is allowed to access a document.

---

# 6. Identity and Authentication Layer

Supabase Auth is responsible for authentication.

The platform uses:

```text
Supabase Auth
      │
      ▼
JWT
      │
      ▼
FastAPI
      │
      ▼
Profile resolution
      │
      ▼
Application authorization
```

Authentication establishes:

> Who is making this request?

Authorization establishes:

> What is this identity allowed to do?

These concerns must remain separate.

Detailed authentication requirements are defined in:

`docs/security/authentication.md`

---

# 7. Authorization Layer

Authorization is enforced by the backend before sensitive resources are accessed.

The platform uses:

- Roles
- Permissions
- Department membership
- Document ownership
- Document classification
- Explicit document permissions
- Administrative privileges

The default policy is:

```text
No explicit permission
        ↓
      DENY
```

Authorization must occur before retrieval.

The secure RAG invariant is:

```text
Unauthorized document
        ↓
Must never become
        ↓
Retrieved context
        ↓
LLM input
```

Detailed authorization rules are defined in:

`docs/security/authorization.md`

---

# 8. Database Security

Supabase PostgreSQL is the authoritative relational database.

It stores:

- Profiles
- Roles
- Permissions
- User-role relationships
- Role-permission relationships
- Departments
- Documents
- Document permissions
- Audit records
- Conversation metadata
- Other application state

## 8.1 Row Level Security

Supabase RLS provides an additional database-level protection layer.

RLS should enforce appropriate access policies for database operations.

However:

```text
RLS ≠ application authorization
```

FastAPI must still enforce business-level authorization.

This prevents the architecture from depending on a single security layer.

---

# 9. Supabase Service Role Security

The Supabase `service_role`/secret key has elevated privileges and can bypass RLS.

Therefore:

- It must never be exposed to the frontend.
- It must never be committed to Git.
- It must never appear in client-side JavaScript.
- It must only be used by trusted server-side code.
- Access must be limited to components that actually require it.
- Production secrets must be managed through secure environment configuration.

The frontend should use the public client configuration intended for browser use.

---

# 10. Document Security

Enterprise documents are considered sensitive by default.

The document lifecycle is:

```text
Upload
  ↓
Validation
  ↓
Metadata creation
  ↓
Private Storage
  ↓
Parsing
  ↓
Security inspection
  ↓
Chunking
  ↓
Embedding
  ↓
Qdrant Cloud indexing
```

Documents should not be treated as trusted merely because an authenticated user uploaded them.

Uploaded content may contain:

- Prompt injections
- Malicious instructions
- Sensitive information
- Unexpected file structures
- Oversized content
- Poisoned RAG content

The ingestion pipeline therefore acts as a security boundary.

---

# 11. Storage Architecture

## 11.1 Supabase Storage

Supabase Storage stores original enterprise documents.

The bucket should be private.

The frontend should not receive unrestricted storage access.

Document downloads should be mediated through appropriate authorization checks.

---

## 11.2 PostgreSQL

PostgreSQL stores authoritative metadata such as:

```text
document_id
owner_id
department_id
classification
storage_path
status
created_at
updated_at
```

PostgreSQL determines whether the document exists and who should be allowed to access it.

---

## 11.3 Qdrant Cloud

Qdrant Cloud stores derived retrieval data.

A vector payload should contain sufficient authorization metadata to construct secure filters.

Example:

```text
{
    document_id,
    chunk_id,
    department_id,
    classification,
    allowed_roles,
    allowed_users
}
```

Qdrant Cloud should never become the authoritative source for application permissions.

---

# 12. RAG Security Architecture

The secure RAG pipeline is:

```text
Authenticated User
        │
        ▼
Query Validation
        │
        ▼
Identity Resolution
        │
        ▼
Authorization Evaluation
        │
        ▼
Permission Filter Construction
        │
        ▼
Vector / Keyword Retrieval
        │
        ▼
Authorization Verification
        │
        ▼
Optional Reranking
        │
        ▼
Context Validation
        │
        ▼
LLM
        │
        ▼
Output Validation
        │
        ▼
Citations + Response
```

The important property is that authorization happens before sensitive context reaches the model.

Retrieval should therefore be permission-aware rather than:

```text
retrieve everything
      ↓
ask LLM to ignore unauthorized information
```

The latter is not a security boundary.

---

# 13. Prompt-Injection Security

All of the following are treated as untrusted data:

- User prompts
- Uploaded documents
- Retrieved chunks
- Conversation history
- External content
- Tool outputs
- Search results

The system must maintain a distinction between:

```text
Application instructions
        vs.
Untrusted data
```

Retrieved documents must not be allowed to redefine:

- Authorization policy
- System instructions
- Tool permissions
- Security rules
- Administrative privileges

Prompt-injection defenses are described in:

`docs/security/prompt-injection.md`

OWASP identifies prompt injection as a major LLM application risk and recommends layered mitigations rather than relying on a single prompt-level defense.

---

# 14. API Security

FastAPI endpoints must follow a consistent security pipeline:

```text
Request
  ↓
Transport security
  ↓
Authentication
  ↓
Input validation
  ↓
Authorization
  ↓
Business logic
  ↓
Audit logging
  ↓
Response validation
```

Sensitive endpoints must never rely exclusively on frontend restrictions.

Examples:

```text
POST /chat
POST /documents
GET  /documents/{id}
DELETE /documents/{id}
POST /admin/users
POST /admin/roles
```

Each endpoint must explicitly define:

- Authentication requirement
- Required permission
- Input schema
- Resource-level authorization
- Audit requirements
- Error behavior

---

# 15. Input Validation

All externally supplied input must be validated.

Inputs include:

- Chat prompts
- Document metadata
- File uploads
- IDs
- Pagination parameters
- Search parameters
- Admin configuration
- Tool parameters

Validation should enforce:

- Correct data types
- Maximum lengths
- Allowed enumerations
- File-size limits
- MIME/type restrictions
- Safe identifier formats
- Pagination limits
- Resource limits

Validation is not a replacement for authorization.

---

# 16. Output Security

Generated responses must not automatically be considered trustworthy.

The application should validate:

- Citation references
- Referenced document IDs
- Citation permissions
- Response size
- Structured output schemas
- Tool actions
- Sensitive output where appropriate

If a generated citation refers to an unauthorized document, the citation must be rejected.

The system should prefer:

```text
No valid authorized evidence
        ↓
Controlled uncertainty / abstention
```

rather than fabricating an answer.

---

# 17. Network Security

The local deployment should minimize exposed services.

Recommended architecture:

```text
Internet
   │
   ▼
Frontend / API entrypoint
   │
   ▼
FastAPI
   │
   ├── Supabase
   ├── Qdrant Cloud
   └── Ollama
```

Internal services should not be unnecessarily exposed to the public network.

In particular:

- Qdrant Cloud should not be publicly accessible unless explicitly required.
- Ollama should not be publicly accessible.
- Internal service ports should be restricted.
- Administrative interfaces should require authentication.
- Production deployment should use HTTPS.

The attack surface should be minimized as the system evolves. OWASP recommends identifying exposed entry points, valuable assets, and the controls protecting those paths, then reducing unnecessary attack surface where possible.

---

# 18. Secrets and Configuration

Secrets must never be hardcoded.

Sensitive configuration includes:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL
QDRANT_API_KEY
OLLAMA configuration
JWT-related secrets where applicable
External API keys
```

Rules:

- `.env` files containing secrets must not be committed.
- `.env.example` contains placeholders only.
- Secrets must not appear in logs.
- Secrets must not be sent to the frontend unless explicitly designed for public use.
- Production secrets must be managed outside source control.
- Credentials should be rotated when compromised.

---

# 19. Rate Limiting and Resource Protection

AI workloads can be computationally expensive.

The platform should protect:

- Chat endpoints
- Document uploads
- Document ingestion
- Embedding generation
- Administrative APIs
- Search endpoints

Controls include:

- Per-user rate limits
- Request-size limits
- Upload-size limits
- Maximum retrieved chunks
- Maximum context size
- Model generation limits
- Concurrency limits
- Timeouts
- Queueing for expensive background operations

Resource controls protect both availability and cost.

---

# 20. Audit Logging

Security-relevant events must be auditable.

Examples:

```text
LOGIN
LOGIN_FAILURE
LOGOUT
USER_CREATED
USER_DISABLED
ROLE_ASSIGNED
ROLE_REMOVED
PERMISSION_CHANGED
DOCUMENT_UPLOADED
DOCUMENT_DELETED
DOCUMENT_ACCESS_DENIED
RAG_QUERY
ADMIN_ACTION
SECURITY_EVENT
RATE_LIMIT_TRIGGERED
```

Audit records should include information such as:

```text
event_id
actor_user_id
event_type
resource_type
resource_id
timestamp
result
request/correlation ID
metadata
```

Logs must not contain:

- Passwords
- Access tokens
- Refresh tokens
- API keys
- Secret values
- Unnecessary document contents

Audit logs should have stronger modification controls than ordinary application data.

---

# 21. Observability and Security Monitoring

The system should generate enough telemetry to detect abnormal behavior.

Important signals include:

- Repeated authentication failures
- Repeated authorization failures
- Unusual document access
- Large retrieval requests
- Excessive uploads
- Prompt-injection detections
- Repeated rate-limit violations
- Administrative privilege changes
- Unexpected service failures
- Model resource exhaustion

Security events should be correlated using request or correlation IDs.

---

# 22. Model Security

Ollama is an internal model execution service.

The LLM must not directly control:

- Database permissions
- User roles
- Authentication
- Storage permissions
- Security policies

The model should receive only authorized context.

The model should also operate under explicit constraints regarding:

- Tool usage
- Output format
- Citation requirements
- Uncertainty
- Sensitive information
- External instructions

---

# 23. Agent and Tool Security

LangGraph agents may eventually execute tools.

Tool execution introduces an additional security boundary.

Each tool must define:

```text
Tool identity
Allowed callers
Required permission
Input schema
Allowed resources
Side effects
Audit requirements
```

Example:

```text
Tool: delete_document

Required permission:
documents.delete

Allowed actor:
authorized authenticated user

Additional requirement:
user must have access to target document
```

The LLM must never be able to bypass these checks.

A tool call should follow:

```text
LLM proposes action
        ↓
Application validates tool call
        ↓
Authorization check
        ↓
Input validation
        ↓
Optional human approval
        ↓
Tool execution
        ↓
Audit event
```

---

# 24. Docker and Runtime Security

Containers should follow least privilege.

Requirements include:

- Minimal base images
- Regular image updates
- No unnecessary packages
- Non-root containers where practical
- Read-only filesystems where practical
- Restricted network exposure
- No unnecessary Linux capabilities
- Secrets provided through runtime configuration
- Resource limits
- Health checks

Development and production configurations should be separated.

Docker should not be treated as a complete security boundary.

---

# 25. Dependency Security

The project depends on:

- Python packages
- Node packages
- Docker images
- LangChain/LangGraph components
- Qdrant Cloud client libraries
- Supabase libraries
- Next.js dependencies
- Model artifacts

Dependency management should include:

- Version pinning or controlled version ranges
- Regular updates
- Vulnerability scanning
- Removal of unused dependencies
- Review of new dependencies
- Lock files committed to source control
- Reproducible builds where practical

Security-sensitive dependencies should receive additional review.

---

# 26. Backup and Recovery

Critical data should have a recovery strategy.

Important assets include:

```text
Supabase PostgreSQL
Supabase Storage documents
Application configuration
RAG metadata
Qdrant Cloud index
Audit logs
```

Because Qdrant Cloud is a derived index, the architecture should allow:

```text
PostgreSQL + Storage
        ↓
Re-run ingestion
        ↓
Rebuild Qdrant Cloud
```

Therefore:

```text
Qdrant Cloud loss
    ≠
Permanent document loss
```

Recovery procedures should be documented and tested.

---

# 27. Fail-Secure Behavior

Security-sensitive failures should default to denial.

Examples:

### Authorization service unavailable

```text
Cannot determine permission
        ↓
DENY
```

### Invalid JWT

```text
Invalid authentication
        ↓
401
```

### Missing permission

```text
No permission
        ↓
403
```

### Qdrant Cloud authorization filter failure

```text
Cannot safely construct filter
        ↓
Do not retrieve
```

### Citation cannot be validated

```text
Invalid citation
        ↓
Do not expose citation
```

The system should never fail open because a security dependency is unavailable.

Secure defaults and fail-secure behavior are core secure architecture principles.

---

# 28. Security Testing Architecture

Security testing must exist at multiple levels.

## Unit Tests

Test:

- Permission decisions
- JWT validation
- Input validation
- Document authorization
- Retrieval filters
- Prompt-injection detection
- Citation validation

## Integration Tests

Test:

- FastAPI + Supabase
- FastAPI + Qdrant Cloud
- Secure RAG
- Storage authorization
- Audit logging

## Security Tests

Test:

- IDOR
- Privilege escalation
- Unauthorized document retrieval
- Prompt injection
- Indirect prompt injection
- RAG poisoning
- Malicious uploads
- Rate-limit bypass
- Secret exposure
- Administrative endpoint abuse

## Adversarial Tests

Test scenarios where:

- A user attempts to access another department's document.
- A document instructs the model to ignore system instructions.
- A user tries to retrieve restricted content through semantic search.
- A malicious prompt attempts to manipulate citations.
- A user attempts to invoke an unauthorized tool.

---

# 29. Security Invariants

The following properties must always remain true.

### Invariant 1 — Authentication

```text
Protected endpoint
    → authenticated identity required
```

### Invariant 2 — Authorization

```text
No explicit permission
    → deny
```

### Invariant 3 — Retrieval

```text
Unauthorized document
    → never retrieved into model context
```

### Invariant 4 — Storage

```text
Private document
    → never publicly accessible
```

### Invariant 5 — Secrets

```text
Server secret
    → never exposed to frontend
```

### Invariant 6 — Model

```text
LLM
    → cannot define authorization policy
```

### Invariant 7 — Tools

```text
LLM tool request
    → application authorization required
```

### Invariant 8 — Failure

```text
Security decision unavailable
    → deny
```

### Invariant 9 — Audit

```text
Security-sensitive administrative action
    → auditable
```

### Invariant 10 — Derived Data

```text
Qdrant Cloud
    → never becomes authoritative permission state
```

---

# 30. Security Architecture Change Requirements

Security review is required when any of the following changes:

- Authentication mechanism
- Authorization model
- New role
- New permission
- New document classification
- New storage system
- New external API
- New agent/tool
- New model
- New public endpoint
- New service
- New data type containing sensitive information
- New network boundary
- New deployment environment
- Major dependency
- Database schema affecting permissions
- RAG retrieval architecture

Architecture changes should trigger a review of:

```text
Attack surface
Trust boundaries
Data flows
Authorization
Secrets
Logging
Threat model
Security tests
```

OWASP recommends revisiting threat modeling and security analysis as architecture, interfaces, user types, and attack surfaces change.

---

# 31. Relationship Between Security Documents

```text
security-architecture.md
        │
        ├── authentication.md
        │
        ├── authorization.md
        │
        ├── prompt-injection.md
        │
        └── threat-model.md
```

Responsibilities:

| Document                   | Purpose                                          |
| -------------------------- | ------------------------------------------------ |
| `security-architecture.md` | Overall security architecture and controls       |
| `authentication.md`        | Identity and authentication                      |
| `authorization.md`         | Permissions and access control                   |
| `prompt-injection.md`      | AI-specific instruction/data security            |
| `threat-model.md`          | Threats, attackers, assets, and attack scenarios |

This separation prevents the architecture document from becoming a duplicate of individual security specifications.

---

# 32. Definition of Done

The security architecture is considered implemented when:

- [ ] Authentication boundary is clearly defined.
- [ ] Authorization boundary is clearly defined.
- [ ] Trust zones are documented.
- [ ] PostgreSQL is authoritative for permissions.
- [ ] Qdrant Cloud is treated as a derived retrieval index.
- [ ] Supabase Storage is private.
- [ ] Backend authorization occurs before retrieval.
- [ ] Unauthorized chunks cannot reach the LLM.
- [ ] Prompt-injection defenses are integrated into the RAG pipeline.
- [ ] Secrets are separated from source code.
- [ ] Internal services are not unnecessarily exposed.
- [ ] Rate limits and resource controls exist.
- [ ] Security events are auditable.
- [ ] Tool execution is authorization-controlled.
- [ ] Containers follow least-privilege principles.
- [ ] Security failures default to denial.
- [ ] Security tests cover critical invariants.
- [ ] Threat modeling is updated after major architecture changes.
- [ ] Backup and recovery procedures are documented.
- [ ] Security architecture remains consistent with the implementation.

---

# 33. Related Documentation

- `docs/architecture/system.md`
- `docs/architecture/backend.md`
- `docs/architecture/data-model.md`
- `docs/architecture/integrations.md`
- `docs/security/authentication.md`
- `docs/security/authorization.md`
- `docs/security/prompt-injection.md`
- `docs/security/threat-model.md`
- `docs/development/testing-strategy.md`
- `docs/rag/retrieval.md`
- `docs/rag/generation.md`
- `docs/deployment/docker.md`
- `docs/deployment/production.md`

---

# 34. External Security Guidance

The architecture uses OWASP guidance as a reference for secure product design, attack-surface analysis, threat modeling, and application security.

Primary reference:

- OWASP Cheat Sheet Series
- OWASP Secure Product Design
- OWASP Attack Surface Analysis
- OWASP Threat Modeling
- OWASP Developer Guide

The OWASP Cheat Sheet Series provides practical application-security guidance for developers and defenders.
