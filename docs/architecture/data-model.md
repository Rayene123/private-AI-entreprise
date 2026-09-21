# Data Model Architecture

## 1. Purpose

This document defines the conceptual relational data model for the Private Enterprise AI Platform after the migration to Supabase.

The data model must support:

- Supabase-managed authentication identity
- Application profiles
- Role-based access control
- Department-based access control
- Document ownership and permissions
- RAG document metadata
- Document chunks and ingestion state
- Audit logging
- Future administration and observability

The database provider is Supabase PostgreSQL.

The core security principle is:

> Authorization data is part of the application's security boundary and must be persisted and validated independently of the LLM.

---

# 2. Supabase-Managed vs Application-Managed Data

Supabase manages authentication users in:

```text
auth.users
```

The application manages domain data in `public`:

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

The application must not duplicate password or authentication secrets into `public.profiles`.

---

# 3. Authentication Model

The platform does not use a custom application user credential table.

The model is:

```text
auth.users
     │
     │ 1:1
     ▼
public.profiles
```

`auth.users` is managed by Supabase Auth. `public.profiles` contains application-specific user information.

---

# 4. Core Entity Model

```text
auth.users
    │
    ▼
profiles
    │
    ├── departments
    │
    └── user_roles
              │
              ▼
            roles
              │
              ▼
        role_permissions
              │
              ▼
          permissions
```

Documents:

```text
documents
    │
    ├── document_permissions
    │
    └── document_chunks
                         │
                         ▼
                       Qdrant Cloud
```

Audit:

```text
profiles
    │
    ▼
audit_logs
```

Application-managed tables:

1. `profiles`
2. `departments`
3. `roles`
4. `permissions`
5. `user_roles`
6. `role_permissions`
7. `documents`
8. `document_permissions`
9. `document_chunks`
10. `audit_logs`

---

# 5. Profiles

```text
profiles
```

Represents application-specific identity and status for a Supabase Auth user.

Fields:

```text
id                  UUID PRIMARY KEY REFERENCES auth.users(id)
first_name          VARCHAR NOT NULL
last_name           VARCHAR NOT NULL
department_id       UUID REFERENCES departments(id)
is_active           BOOLEAN NOT NULL DEFAULT TRUE
is_superuser        BOOLEAN NOT NULL DEFAULT FALSE
last_login_at       TIMESTAMP
created_at          TIMESTAMP NOT NULL
updated_at          TIMESTAMP NOT NULL
```

`profiles` must not contain plaintext passwords, password credentials, refresh tokens, Supabase service-role keys, or authentication secrets.

Authentication email and credentials are managed by Supabase Auth in `auth.users`.

---

# 6. Departments

```text
departments
```

Represents an organizational department.

Fields:

```text
id              UUID PRIMARY KEY
name            VARCHAR NOT NULL UNIQUE
description     TEXT
is_active       BOOLEAN NOT NULL DEFAULT TRUE
created_at      TIMESTAMP NOT NULL
updated_at      TIMESTAMP NOT NULL
```

Examples include HR, Finance, Engineering, Sales, Legal, and IT.

---

# 7. Roles and Permissions

Roles:

```text
roles

id              UUID PRIMARY KEY
name            VARCHAR NOT NULL UNIQUE
description     TEXT
created_at      TIMESTAMP NOT NULL
updated_at      TIMESTAMP NOT NULL
```

Initial roles:

```text
ADMIN
MANAGER
EMPLOYEE
```

Permissions:

```text
permissions

id              UUID PRIMARY KEY
name            VARCHAR NOT NULL UNIQUE
description     TEXT
created_at      TIMESTAMP NOT NULL
updated_at      TIMESTAMP NOT NULL
```

Example permissions:

```text
documents:read
documents:write
documents:delete
documents:share
users:read
users:write
audit:read
admin:write
```

Permissions should remain granular. A permission represents an action, not a business role.

---

# 8. User Roles

```text
user_roles

profile_id  UUID NOT NULL REFERENCES profiles(id)
role_id     UUID NOT NULL REFERENCES roles(id)
created_at  TIMESTAMP NOT NULL

PRIMARY KEY(profile_id, role_id)
```

The permission chain is:

```text
Profile
 ↓
UserRole
 ↓
Role
 ↓
RolePermission
 ↓
Permission
```

---

# 9. Role Permissions

```text
role_permissions

role_id        UUID NOT NULL REFERENCES roles(id)
permission_id  UUID NOT NULL REFERENCES permissions(id)
created_at     TIMESTAMP NOT NULL

PRIMARY KEY(role_id, permission_id)
```

---

# 10. Documents

```text
documents
```

Represents an uploaded enterprise document and is the primary security boundary for RAG content.

Fields:

```text
id                       UUID PRIMARY KEY
title                    VARCHAR NOT NULL
description              TEXT
filename                 VARCHAR NOT NULL
storage_bucket           TEXT NOT NULL
storage_path             TEXT NOT NULL
mime_type                VARCHAR NOT NULL
file_size                BIGINT NOT NULL
checksum                 VARCHAR NOT NULL
owner_id                 UUID REFERENCES profiles(id)
department_id            UUID REFERENCES departments(id)
classification           VARCHAR NOT NULL
status                   VARCHAR NOT NULL
ingestion_status         VARCHAR NOT NULL
ingestion_error          TEXT
ingestion_started_at     TIMESTAMP
ingestion_completed_at   TIMESTAMP
version                  INTEGER NOT NULL DEFAULT 1
created_at               TIMESTAMP NOT NULL
updated_at               TIMESTAMP NOT NULL
deleted_at               TIMESTAMP
```

`storage_bucket` and `storage_path` point to the source object in Supabase Storage.

Initial classifications:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

Classification is metadata used by authorization. It is not the only authorization mechanism.

---

# 11. Document Permissions

```text
document_permissions

id              UUID PRIMARY KEY
document_id     UUID NOT NULL REFERENCES documents(id)
profile_id      UUID REFERENCES profiles(id)
role_id         UUID REFERENCES roles(id)
permission      VARCHAR NOT NULL
granted         BOOLEAN NOT NULL DEFAULT TRUE
created_at      TIMESTAMP NOT NULL
expires_at      TIMESTAMP
```

Possible permissions:

```text
read
write
delete
share
```

The application must define precedence for explicit grants, explicit denials, role policies, department rules, classification rules, and default deny.

---

# 12. Document Chunks

```text
document_chunks

id              UUID PRIMARY KEY
document_id     UUID NOT NULL REFERENCES documents(id)
chunk_index     INTEGER NOT NULL
content         TEXT NOT NULL
page_number     INTEGER
section_title   TEXT
token_count     INTEGER
content_hash    VARCHAR NOT NULL
created_at      TIMESTAMP NOT NULL
updated_at      TIMESTAMP NOT NULL

UNIQUE(document_id, chunk_index)
```

A chunk is not an independent security object. It inherits its security context from the parent document.

---

# 13. Audit Logs

```text
audit_logs

id              UUID PRIMARY KEY
profile_id      UUID REFERENCES profiles(id)
auth_user_id    UUID REFERENCES auth.users(id)
event_type      VARCHAR NOT NULL
action          VARCHAR NOT NULL
resource_type   VARCHAR
resource_id     UUID
status          VARCHAR NOT NULL
ip_address      INET
user_agent      TEXT
metadata        JSONB
created_at      TIMESTAMP NOT NULL
```

Audit logs must not contain passwords, access tokens, API keys, secrets, full confidential document contents, or unnecessary sensitive user data.

---

# 14. Vector Database Relationship

Qdrant Cloud is a derived retrieval index.

```text
Supabase PostgreSQL
    │
    └── document_chunks
            │
            └── chunk_id
                  ↓
               Qdrant Cloud
                  │
                  └── vector + metadata
```

Supabase PostgreSQL remains the source of truth for profiles, roles, permissions, documents, authorization, audit data, and chunk metadata.

---

# 15. Qdrant Cloud Metadata Requirements

Every indexed chunk should contain enough metadata for permission-aware retrieval.

Minimum payload:

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
  "document_version": 1,
  "chunk_index": 4,
  "page_number": 7
}
```

Authorization filters must be constructed from trusted server-side identity and policy data.

The user must never be allowed to directly provide an authorization filter such as:

```json
{
  "department_id": "finance"
}
```

and thereby bypass authorization.

---

# 16. Supabase RLS

Supabase Row Level Security should be enabled on appropriate application tables exposed through Supabase APIs.

RLS can enforce defense in depth for profiles, documents, document metadata, audit visibility, and administrative tables.

RLS is not a replacement for FastAPI authorization. FastAPI remains responsible for application policy and RAG retrieval permissions.

---

# 17. Ingestion State

Documents should track ingestion/indexing state:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

A document should not become retrievable until the source file is stored, metadata is persisted, chunks are created, embeddings are generated, Qdrant Cloud indexing succeeds, and ingestion status is marked `COMPLETED`.

---

# 18. Indexing Strategy

Initial indexes:

```text
profiles.department_id
documents.owner_id
documents.department_id
documents.classification
documents.status
documents.ingestion_status
document_chunks.document_id
document_chunks.content_hash
document_permissions.document_id
document_permissions.profile_id
document_permissions.role_id
audit_logs.profile_id
audit_logs.auth_user_id
audit_logs.event_type
audit_logs.resource_id
audit_logs.created_at
```

Composite indexes should be introduced based on actual query patterns.

---

# 19. Security Invariants

- Every application profile references a Supabase Auth user.
- No application table stores authentication secrets.
- Every document has a valid security classification.
- Every document chunk belongs to exactly one document.
- Authorization is determined from trusted database state and application policy.
- Qdrant Cloud metadata must correspond to Supabase PostgreSQL entities.
- Deleting or disabling a profile must not destroy audit history.
- Unauthorized document content must never be passed to the generation layer.
- A missing authorization decision results in denial.
- Qdrant Cloud must never become the authoritative source for authorization.

---

# 20. Migration Strategy

Database changes must be managed through migrations.

Supabase migrations or Alembic migrations may be used depending on the chosen workflow, but schema changes must be versioned, reproducible, reviewable, and reversible where practical.

Do not manually modify production database schemas.

Initial application table order:

```text
1. departments
2. profiles
3. roles
4. permissions
5. user_roles
6. role_permissions
7. documents
8. document_permissions
9. document_chunks
10. audit_logs
```

`auth.users` is created and managed by Supabase Auth.

---

# 21. Related Documents

- `docs/architecture/system.md`
- `docs/architecture/backend.md`
- `docs/architecture/integrations.md`
- `docs/security/authentication.md`
- `docs/security/authorization.md`
- `docs/security/threat-model.md`
- `docs/rag/ingestion.md`
- `docs/rag/retrieval.md`
