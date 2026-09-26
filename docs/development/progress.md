# Development Progress

## Project

**Private Enterprise AI Platform**

A self-hosted enterprise AI platform with permission-aware RAG, local LLM inference, RBAC, hybrid retrieval, citations, audit logging, security controls, observability, and Docker-based deployment.

---

## Current Status

| Field          | Value                                                          |
| -------------- | -------------------------------------------------------------- |
| Current phase  | Module 6 — Secure Document Storage & File Access               |
| Current module | Private document file storage and access control               |
| Status         | Implemented; automated tests passed; live verification pending |
| Last updated   | 2026-09-26                                                     |

---

# Completed

## Project Planning

- [x] Core project idea defined
- [x] Main architecture defined
- [x] Technology stack selected
- [x] Development phases defined
- [x] Security principles defined
- [x] Documentation structure created

## Repository Structure

- [x] Backend directory structure created
- [x] Frontend directory structure created
- [x] Data directory structure created
- [x] Scripts directory created
- [x] Documentation directories created
- [x] Docker directory created

## Documentation

- [x] `docs/README.md`
- [x] Architecture documentation files created
- [x] Security documentation files created
- [x] Development documentation files created
- [x] RAG documentation files created
- [x] Deployment documentation files created
- [x] `docs/development/phases.md`

## Backend Foundation

- [x] FastAPI application entry point created
- [x] Environment-backed settings created
- [x] Reusable logging configuration created
- [x] `/health` endpoint created
- [x] Backend environment template created
- [x] Backend tests added for health and settings
- [x] Consistent API error handling created
- [x] Supabase integration boundary created
- [x] Supabase Auth JWT validation boundary created
- [x] User profiles and RBAC foundation created
- [x] Document metadata and document-level authorization foundation created

---

# Current Work

## Module 5 — Document Management & Document-Level Access Control

### Document Metadata and Access Control

**Status:** IMPLEMENTED AND LIVE-VERIFIED

### Objective

Create the secure metadata and authorization foundation for enterprise documents before later ingestion, parsing, embeddings, vector search, and RAG modules.

### Completed

- [x] `public.documents` migration added
- [x] `public.document_user_access` migration added
- [x] Document ownership is stored in `documents.owner_id`
- [x] Documents may belong to `departments`
- [x] Access levels constrained to `private`, `department`, and `organization`
- [x] Status constrained to `active` and `archived`
- [x] Useful indexes added for owner, department, status, access level, and explicit access lookups
- [x] RLS enabled on document tables as defense in depth
- [x] Ordinary authenticated users cannot mutate `document_user_access`
- [x] `DocumentService` added for create, list, get, update, and archive-delete operations
- [x] Document-level authorization added for ownership, department access, organization access, private access, explicit user access, and inactive profiles
- [x] `POST /documents`, `GET /documents`, `GET /documents/{id}`, `PATCH /documents/{id}`, and `DELETE /documents/{id}` added
- [x] Client-supplied `owner_id` is rejected by request validation and ownership is derived from the authenticated user
- [x] Existing Module 4 RBAC permissions are reused: `documents.create`, `documents.read`, `documents.update`, and `documents.delete`
- [x] Tests added for authentication, permissions, access boundaries, owner spoofing, update, delete, inactive users, and endpoint behavior
- [x] Local backend suite verified: `73 passed, 1 warning`

### Deferred

Module 5 intentionally does not implement file upload, Supabase Storage upload/download, document parsing, PDF extraction, OCR, chunking, embeddings, Qdrant indexing, vector search, RAG, LLM retrieval, LangGraph, agents, frontend document UI, or admin dashboards.

### Verification Result

Local and live verification completed on 2026-09-23:

- `pytest -q`: `73 passed, 1 warning`
- `GET /health`: `200 {"status": "ok"}`
- `GET /documents` without authentication: `401 authentication_required`

- Temporary credentials were used only in memory for the three dedicated test accounts and rotated away after verification.
- Organization, department, private, explicit-access grant/revocation, ownership, update, archive-delete, inactive-profile, and authentication-boundary behavior were verified through the FastAPI API.
- Existing RBAC was preserved: employee document creation was correctly denied because the employee role lacks `documents.create`; manager and admin creation paths were verified instead.
- Test documents were archived, explicit access was removed, and test profiles were restored.
- Basic API database checks verified table columns, enum constraints, and foreign-key enforcement.
- PostgreSQL catalog-level RLS and index verification remains a Supabase SQL Editor check.

## Module 6 — Secure Document Storage & File Access

### Private Storage and File Access

**Status:** IMPLEMENTED AND LIVE-VERIFIED

### Completed

- [x] Private `enterprise-documents` Supabase Storage bucket configuration added
- [x] Restrictive `storage.objects` defense-in-depth policy added
- [x] Server-generated `documents/{document_id}/{generated_filename}` paths added
- [x] Upload and download authorization reuses Module 4 RBAC and Module 5 document-level checks
- [x] Archived document downloads are blocked
- [x] MIME, size, filename, and file-signature validation added
- [x] Replacement metadata synchronization and failed-update cleanup added
- [x] Storage architecture documentation added
- [x] Complete backend suite verified: `112 passed, 2 warnings`
- [x] Live bucket metadata verified: bucket exists and is private
- [x] Live authentication, upload, download, unauthorized access, department/private access, replacement, archive protection, and cleanup verified

### Verification Result

Automated tests, live bucket metadata verification, and end-to-end functional
verification passed on 2026-09-26 using disposable test identities and
documents. Temporary users, documents, and Storage objects were removed after
verification. PostgreSQL catalog-level RLS and constraint inspection remains a
Supabase SQL Editor check.

---

## Module 4 — User Profiles & RBAC Foundation

### Profiles, Roles, Permissions

**Status:** COMPLETE

### Objective

Create the initial application identity and authorization foundation from Supabase Auth users to application profiles, roles, and permissions.

### Completed

- [x] `public.profiles` references `auth.users(id)`
- [x] `departments`, `roles`, `permissions`, `user_roles`, and `role_permissions` migration added
- [x] Deterministic seed roles: `admin`, `manager`, `employee`
- [x] Deterministic seed permissions for profiles, users, documents, and chat
- [x] Role-permission mappings seeded
- [x] Auth user insert trigger creates an application profile
- [x] New profiles receive the default `employee` role
- [x] RLS enabled for profile and RBAC tables
- [x] Minimal own-profile select/update policy added
- [x] Authorization service added for roles and permissions
- [x] Reusable `require_permission()` dependency added
- [x] `GET /users/me` returns profile, roles, and permissions
- [x] Tests cover RBAC resolution, permission dependency behavior, `/users/me`, and privilege mutation non-routes
- [x] Live Supabase schema and RLS behavior verified for all Module 4 tables
- [x] Live seed roles, permissions, and role-permission mappings verified
- [x] Live Auth-to-profile trigger verified for employee, manager, and admin test users
- [x] Live employee, manager, and admin role assignments verified
- [x] Live `/users/me` responses verified for all three test users
- [x] Live 401, 403, and `users.manage` authorization boundaries verified
- [x] Live profile update restrictions verified: only `display_name` is writable by authenticated users

### Live Verification Result

Module 4 is **Completed and live-verified**.

Verified roles:

- Employee: `employee`
- Manager: `employee`, `manager`
- Admin: `employee`, `admin`

Verified permissions:

- Employee: `profile.read`, `profile.update`, `documents.read`, `chat.use`
- Manager: `profile.read`, `profile.update`, `users.read`, `documents.read`, `documents.create`, `documents.update`, `chat.use`
- Admin: all nine seeded permissions, including `users.manage` and `documents.delete`

Verified behavior:

- The Auth user trigger created all three `public.profiles` rows and default `employee` role rows.
- `GET /users/me` returned the expected live roles and permissions.
- No JWT returned `401`.
- Employee and manager requests requiring `users.manage` returned `403`; admin was allowed.
- Authenticated users could update only `profiles.display_name`; `is_active`, `department_id`, `user_roles`, and `role_permissions` mutations were blocked.
- Ordinary authenticated reads of RBAC tables returned no rows, while administrative reads remained available through the service context.

---

# Next Modules

After this module:

```text
Document parsing, chunking, embeddings, and RAG retrieval
```

---

# Architecture Decisions

## Backend

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Supabase Python client

## Frontend

- Next.js
- TypeScript
- Tailwind CSS

## AI / RAG

- Local LLM inference through Ollama
- Sentence Transformers for embeddings
- Qdrant Cloud for vector storage
- Hybrid retrieval
- Reranking
- LangGraph for controlled orchestration

## Security

- JWT authentication
- Secure password hashing
- RBAC
- Department-based access control
- Document-level permissions
- Permission-aware retrieval
- Prompt-injection defenses
- Input validation
- File validation
- Rate limiting
- Audit logging

## Infrastructure

- Docker
- Docker Compose
- Persistent volumes
- Environment-based configuration

---

# Critical Security Principles

## Authorization Before Generation

The system must never retrieve confidential information and rely on the LLM to decide whether it should reveal it.

The required boundary is:

```text
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
```

Unauthorized chunks must never enter the LLM context.

## LLM Is Not an Authorization Boundary

Prompts such as:

```text
"Do not reveal confidential information."
```

must never be considered an access-control mechanism.

Authorization is enforced by backend services and retrieval filters.

---

# Current Architecture

```text
                    ┌───────────────┐
                    │    Frontend   │
                    │   Next.js     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    FastAPI    │
                    │    Backend    │
                    └───────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        PostgreSQL       Qdrant Cloud         Ollama
        Identity &      Vector DB       Local LLM
        Metadata
```

RAG flow:

```text
User Query
    ↓
Authentication
    ↓
Authorization
    ↓
Query Analysis
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
Citation Validation
    ↓
Audit Logging
    ↓
Response
```

---

# Module Tracking

| Module                                   | Status           |
| ---------------------------------------- | ---------------- |
| 0.1 Repository Structure                 | COMPLETE         |
| 0.2 Environment Configuration            | COMPLETE         |
| 0.3 Docker Compose                       | NOT STARTED      |
| 0.4 Development Documentation            | COMPLETE         |
| 1.1 Application Entry Point              | COMPLETE         |
| 1.2 Configuration                        | COMPLETE         |
| 1.3 Logging                              | COMPLETE         |
| 1.4 Error Handling                       | COMPLETE         |
| 1.5 Database Connection                  | NOT STARTED      |
| 1.6 Health Checks                        | COMPLETE         |
| 1.7 API Versioning                       | NOT STARTED      |
| 2.x Supabase Integration                 | COMPLETE         |
| 3.x Supabase Authentication              | COMPLETE         |
| 4.x Database & Identity                  | COMPLETE         |
| 4.x Authorization & RBAC                 | COMPLETE         |
| 4.x Document Management & Access Control | COMPLETE IN CODE |
| 4.x Document Ingestion                   | NOT STARTED      |
| 5.x Embeddings & Vector Storage          | NOT STARTED      |
| 6.x Basic Retrieval                      | NOT STARTED      |
| 7.x Permission-Aware Retrieval           | NOT STARTED      |
| 8.x Local LLM & Generation               | NOT STARTED      |
| 9.x Secure RAG Pipeline                  | NOT STARTED      |
| 10.x Security Hardening                  | NOT STARTED      |
| 11.x LangGraph Agent Layer               | NOT STARTED      |
| 12.x Frontend                            | NOT STARTED      |
| 13.x Admin & Observability               | NOT STARTED      |
| 14.x Testing & Evaluation                | NOT STARTED      |
| 15.x Deployment                          | NOT STARTED      |

---

# Known Issues

- Python 3.11 is installed at `C:\Users\rayen\AppData\Local\Programs\Python\Python311\python.exe`, but it is not directly discoverable in the sandboxed shell without elevated execution.
- The local backend virtual environment was created at `backend/.venv`.

---

# Open Decisions

These decisions will be finalized before the modules that depend on them are implemented.

- [x] Initial profile/RBAC PostgreSQL schema
- [ ] Authentication token strategy
- [ ] Initial embedding model
- [ ] Initial Ollama model
- [ ] Chunking strategy
- [ ] Retrieval scoring/fusion strategy
- [ ] Reranker model
- [ ] Document classification model
- [ ] Exact permission model
- [ ] Production deployment target

---

# Session Handoff

## Last Completed

Implemented Module 4: user profiles and RBAC foundation.

## Current Task

Document management and document-level authorization foundation is completed in code and locally verified.

## Next Task

Wait for live Supabase verification or the next explicitly requested module.

## Important Constraints

- Do not implement multiple modules simultaneously.
- Stop after Module 5 until explicitly asked to continue.
- Do not bypass authorization for convenience.
- Do not send unauthorized context to the LLM.
- Keep AI providers abstracted.
- Test each module before moving forward.
- Update this file after every completed module.

---

# Change Log

## 2026-09-21

- Created project repository structure.
- Created documentation structure.
- Defined development phases.
- Defined module-level development workflow.
- Defined critical authorization boundary.
- Created initial project progress tracking.

## 2026-09-22

- Implemented initial FastAPI backend foundation.
- Added environment-backed settings and safe logging setup.
- Added `GET /health` endpoint.
- Added backend environment template, gitignore rules, README, and tests.
- Created local backend virtual environment using Python 3.11.
- Verified tests with `backend/.venv`: 3 passed.
- Verified uvicorn startup and `GET /health` returned `{"status": "ok"}`.
- Added secure default parsing for unexpected `DEBUG` environment values.
- Implemented centralized API error handling.
- Added request ID middleware and structured error responses.
- Verified tests with `backend/.venv`: 11 passed.
- Verified `uvicorn app.main:app --reload`, `GET /health`, and structured 404 response.
- Added official Supabase Python client dependency.
- Created reusable Supabase integration package with user and service client creation paths.
- Added safe missing-configuration and provider-failure behavior.
- Added Supabase integration tests using fakes; normal `pytest` requires no real Supabase credentials.
- Verified tests with `backend/.venv`: 18 passed.
- Verified `uvicorn app.main:app --reload` and `GET /health` still returns `{"status": "ok"}`.
- Migrated Supabase configuration to `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY`.
- Implemented `get_current_user()` and authentication service.
- Added `/auth/me` as a minimal protected endpoint for verifying authentication.
- Added authentication tests for missing, malformed, invalid, expired, wrong issuer, wrong audience, missing subject, valid token, and token-safe logs.
- Verified tests with `backend/.venv`: 34 passed.
- Verified `GET /health` remains public and `GET /auth/me` without a token returns structured `401`.
- Added Module 4 RBAC migration with profiles, departments, roles, permissions, user-role mappings, role-permission mappings, seed data, RLS, and Auth user profile trigger.
- Added authorization service, `require_permission()` dependency, and `GET /users/me`.
- Added tests for profile retrieval, RBAC role/permission checks, 401/403 behavior, privilege mutation non-routes, and service credential non-exposure.
- Verified tests with `backend/.venv`: 46 passed.
- Live-verified Module 4 against Supabase: schema tables, RLS behavior, seeded roles and permissions, Auth-to-profile trigger, employee/manager/admin assignments, `/users/me`, 401/403 boundaries, `users.manage` authorization, and profile update restrictions.
- Verified final backend suite with `backend/.venv`: 50 passed, 2 warnings.

## 2026-09-23

- Implemented Module 5 document metadata schema with `documents` and `document_user_access`.
- Added document status/access constraints, indexes, updated-at trigger, RLS, and restricted grants.
- Added document schemas, service authorization logic, and `/documents` CRUD metadata endpoints.
- Reused Module 4 RBAC permissions for document create/read/update/delete.
- Added tests for document access boundaries, owner spoofing prevention, inactive users, update/delete rules, and endpoint authentication/authorization behavior.
- Verified final backend suite with `backend/.venv`: 72 passed, 2 warnings.
- Verified FastAPI smoke checks: `GET /health` returned 200 and unauthenticated `GET /documents` returned 401.
