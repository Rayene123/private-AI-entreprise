# Authentication Architecture

## 1. Purpose

This document defines the authentication architecture for the Private Enterprise AI Platform.

Authentication is responsible for answering:

> **Who is making this request?**

Authorization is responsible for answering:

> **What is this authenticated user allowed to access?**

These concerns must remain separate.

The platform uses **Supabase Auth** as the authentication provider. Supabase Auth manages user authentication, sessions, access tokens, refresh tokens, and authentication-related lifecycle operations.

The FastAPI backend validates the authenticated user's identity before executing protected application operations.

---

# 2. Authentication Architecture

The Module 3 backend authentication flow is:

```text
Client
        ↓
Authorization: Bearer <JWT>
        ↓
FastAPI
        ↓
get_current_user()
        ↓
AuthenticationService
        ↓
Supabase JWT claims verification
        ↓
AuthenticatedUser
        ↓
Protected endpoint
```

The broader client sign-in/session flow is:

```text
┌────────────────────┐
│      Browser       │
│     Next.js App    │
└─────────┬──────────┘
          │
          │ Sign in
          ▼
┌────────────────────┐
│    Supabase Auth   │
│                    │
│ - Authenticate     │
│ - Create session   │
│ - Issue JWT        │
└─────────┬──────────┘
          │
          │ Access Token
          ▼
┌────────────────────┐
│     Next.js        │
│   Authenticated    │
│      Session       │
└─────────┬──────────┘
          │
          │ Authorization: Bearer <JWT>
          ▼
┌────────────────────┐
│      FastAPI       │
│                    │
│  JWT Validation    │
│  Identity Resolve  │
└─────────┬──────────┘
          │
          │ Authenticated User
          ▼
┌────────────────────┐
│ Authorization      │
│ / Permission       │
│ Service             │
└────────────────────┘
```

The LLM, Qdrant Cloud, and RAG pipeline must never be responsible for determining whether a user is authenticated.

---

# 3. Supabase Auth Responsibilities

Supabase Auth is responsible for:

- user registration
- sign-in
- sign-out
- password management
- email verification where enabled
- authentication sessions
- access tokens
- refresh tokens
- authentication providers
- authentication lifecycle
- optional MFA
- authentication-related user identity

Supabase Auth uses JWTs for authenticated sessions and provides mechanisms for issuing and refreshing these tokens.

The application must not recreate these responsibilities inside FastAPI.

---

# 4. Application Responsibilities

The application will be responsible for:

- resolving the authenticated application user profile
- checking whether the account is active
- loading the user's application profile
- resolving department membership
- resolving roles
- resolving permissions
- enforcing authorization
- creating audit events
- applying enterprise-specific security policies

Module 3 established the authentication boundary. Module 4 adds application
profile lookup and RBAC permission resolution after authentication.

Therefore:

```text
Supabase Auth
      │
      │ "This user is authenticated"
      ▼
FastAPI
      │
      │ "What does this user have access to?"
      ▼
Application Authorization
```

Authentication does not grant access to enterprise resources by itself.

---

# 5. User Identity Model

Supabase maintains the authoritative authentication identity in:

```text
auth.users
```

The application maintains business-specific user information in:

```text
public.profiles
```

The relationship is:

```text
auth.users.id
      │
      │ foreign key
      ▼
profiles.id
```

The Supabase user UUID is the primary identity identifier across the platform.

The application must not create a second independent authentication identity.

---

# 6. Profile Responsibilities

`profiles` contains application-level information such as:

```text
id
display_name
department_id
is_active
created_at
updated_at
```

Depending on the final data model, additional business metadata may be added.

The profile must **not** contain:

```text
password
password_hash
password_salt
authentication_secret
refresh_token
```

Passwords and authentication credentials belong to Supabase Auth.

Supabase Auth stores authentication information in its dedicated `auth` schema rather than exposing those tables through the normal generated API.

---

# 7. JWT Authentication

Supabase Auth issues an access token in JWT format for an authenticated session.

The token contains claims identifying the authenticated user.

Important claims include:

```text
sub
iss
aud
exp
iat
role
session_id
```

The `sub` claim represents the authenticated user's UUID.

The `exp` claim determines when the token expires.

The `iss` claim identifies the issuer.

The `aud` claim identifies the intended audience.

Supabase documents these claims as part of its JWT structure.

---

# 8. FastAPI Authentication Flow

Every protected FastAPI endpoint follows this sequence:

```text
1. Receive request
       │
       ▼
2. Extract Authorization header
       │
       ▼
3. Extract Bearer JWT
       │
       ▼
4. Verify Supabase JWT claims through the supported Supabase client mechanism
       │
       ▼
5. Validate the verified identity claims
       │
       ▼
6. Extract the verified user ID from `sub`
       │
       ▼
7. Create `AuthenticatedUser`
       │
       ▼
8. Continue to the protected endpoint
       │
       ▼
```

If any authentication step fails, the request must stop.

The request must not continue to the protected endpoint when authentication
fails. Profile resolution, authorization, document retrieval, Qdrant Cloud
search, RAG processing, LLM generation, and administrative authorization are
outside the Module 3 authentication boundary.

---

# 9. Authorization Header

Authenticated requests to FastAPI use:

```http
Authorization: Bearer <access_token>
```

The backend must treat the token as untrusted input until it has been cryptographically validated.

A missing or malformed token results in an authentication failure.

Supabase documents the Bearer JWT pattern for authenticated requests.

---

# 10. JWT Validation

The backend does not trust an unverified JWT payload. The authentication
boundary validates the Supabase token using the installed Supabase client's
supported claims-verification mechanism, including the supported
`auth.get_claims()` / JWKS verification path. The application does not
implement its own JWT cryptography.

Validation must include, as appropriate:

- issuer (`iss`)
- audience (`aud`)
- expiration (`exp`)
- signature
- subject (`sub`)

The backend must never simply decode a JWT and trust its contents.

### Incorrect

```text
decode JWT
     ↓
trust `sub`
```

### Correct

```text
JWT
 ↓
cryptographic validation
 ↓
claim validation
 ↓
extract `sub`
 ↓
create `AuthenticatedUser`
```

Supabase provides JWT signing keys and a JWKS endpoint for asymmetric signing configurations. Verification should use an established JWT library or supported Supabase mechanisms rather than implementing cryptographic verification manually.

---

# 11. Authenticated Identity

After successful Supabase claims verification:

```text
verified JWT.sub
   │
   ▼
AuthenticatedUser
```

The verified `sub` claim becomes the authenticated Supabase user ID. Module 4
resolves application roles and permissions from database state. It does not
implement document access policy.

Conceptually:

```text
AuthenticatedUser
├── user_id
└── email (when present in verified claims)
```

Roles and permissions are loaded from trusted backend/database state and must
never be trusted from an unverified or client-provided payload.

---

# 12. Authentication vs Authorization

These two stages must remain separate.

### Authentication

```text
Who is the user?
```

Handled by:

```text
Supabase Auth
+
FastAPI JWT validation
```

### Authorization

```text
What may the user access?
```

Planned for:

```text
FastAPI authorization services
+
PostgreSQL application data
+
RLS where applicable
```

RBAC roles, permissions, profile creation, default employee assignment, and
initial profile/RBAC RLS policies are Module 4 work. Department-based document
authorization and document-level policies remain future work.

Example:

```text
User authenticated
        │
        ▼
User ID = abc-123
        │
        ▼
Is account active?
        │
        ▼
What department?
        │
        ▼
What roles?
        │
        ▼
What permissions?
        │
        ▼
Can this document be accessed?
```

Authentication alone must never imply permission to access enterprise documents.

---

# 13. Client-Side Authentication

The Next.js application uses Supabase Auth for the user-facing authentication experience.

The frontend is responsible for:

- displaying authentication screens
- initiating sign-in
- maintaining the user session through the Supabase client
- detecting authentication state
- refreshing sessions through the supported Supabase flow
- attaching the access token to backend API requests
- redirecting unauthenticated users when appropriate

The frontend must not determine authorization by itself.

For example:

```text
Frontend says:
"You are an admin"

        ↓

Backend:
"Let me verify your authenticated identity
and determine your actual permissions."
```

The backend remains authoritative.

---

# 14. Server-Side Authentication

FastAPI is the security boundary for backend operations.

Protected endpoints should require an authenticated request context.

Conceptually:

```text
GET /api/chat
        │
        ▼
get_current_user()
        │
        ├── invalid → 401
        │
        ▼
protected endpoint
```

Module 3 supplies the authentication dependency. Authorization and RAG
protection are future layers.

---

# 15. Authentication Error Semantics

The API must distinguish authentication failures from authorization failures.

### HTTP 401 — Unauthenticated

Use when:

- token is missing
- token is malformed
- token is expired
- token signature is invalid
- token issuer is invalid
- token audience is invalid
- token claims are invalid
- required identity information is unavailable

Example:

```json
{
  "error": "authentication_required"
}
```

### HTTP 403 — Authenticated but Forbidden

Use when:

- the user is authenticated
- but the user lacks permission for the requested operation

Example:

```json
{
  "error": "insufficient_permissions"
}
```

The API must not reveal sensitive authorization information through error messages.

The project uses the existing structured application error format for
authentication failures. Missing credentials, a malformed authorization
header, an invalid token, an expired token, or invalid claims all result in
`401`. An authenticated user without permission returns `403`.

---

# 15.1 Security Logging

The following must never be logged:

- `Authorization` headers
- access tokens
- refresh tokens
- Supabase secret/service-role keys
- Supabase publishable/anon keys

User IDs may be logged when appropriate for security or audit purposes, but
credentials and JWT contents must not be included.

---

# 16. Inactive Users

Authentication and application account status are separate concerns. Account
status checks are future application profile and authorization work, not part
of Module 3 token authentication.

A user may possess a valid Supabase authentication token while the application profile is no longer active.

Therefore:

```text
Valid JWT
   │
   ▼
Load profile
   │
   ▼
is_active = false
   │
   ▼
Reject request
```

Inactive users must not be allowed to access enterprise resources.

This check occurs before:

- document retrieval
- chat
- administrative APIs
- document ingestion
- other protected application operations

---

# 17. Deleted Users

If the Supabase authentication identity is deleted, the application must not continue treating the corresponding profile as an active enterprise identity.

Foreign-key relationships and application lifecycle rules must be designed so that authentication deletion cannot silently create orphaned privileged accounts.

User deletion behavior must be explicitly defined during database implementation.

---

# 18. Token Expiration and Refresh

Access tokens are short-lived credentials.

Supabase Auth manages sessions using access and refresh tokens and can continuously issue new access tokens while the user remains signed in.

The application should therefore:

```text
Access token expires
        │
        ▼
Supabase session refresh
        │
        ▼
New access token
        │
        ▼
Future API requests
```

The backend must not implement its own parallel refresh-token system.

Refresh tokens must not be sent to arbitrary application services.

---

# 19. Sign-Out

The frontend must use the Supabase Auth sign-out mechanism.

After sign-out:

```text
Client session terminated
        │
        ▼
Future requests require
a valid authenticated session
```

The platform must not rely solely on frontend UI state to determine whether a user is signed out.

For stronger revocation requirements, session and token-revocation behavior must be explicitly designed and tested rather than assumed.

---

# 20. Session Identification

Supabase access tokens include a `session_id` claim that identifies the user's authentication session.

The platform may use this identifier for:

- audit correlation
- security investigation
- session-aware monitoring
- authentication event analysis

The session ID must not be treated as an authorization credential by itself.

---

# 21. Service Role Security

Supabase provides privileged server-side credentials that can bypass normal Row Level Security protections.

These credentials must remain strictly server-side.

They must never be:

- included in the frontend
- committed to Git
- exposed in browser JavaScript
- included in client-side environment variables
- returned by an API endpoint
- logged

The backend may use privileged Supabase credentials only where the operation explicitly requires them and must still enforce application authorization.

---

# 22. RLS Interaction

Supabase Row Level Security is an additional security layer.

The platform's security model is:

```text
Authentication
      ↓
FastAPI identity
      ↓
Application authorization
      ↓
Database access / RLS
```

RLS must not be considered a replacement for FastAPI authorization.

In particular, the RAG pipeline requires authorization before retrieving enterprise content from Qdrant Cloud.

Therefore:

```text
JWT
 ↓
FastAPI
 ↓
Authorization
 ↓
Permission-aware retrieval
 ↓
Qdrant Cloud
 ↓
Authorized context
 ↓
LLM
```

This ensures unauthorized documents do not reach the generation layer.

---

# 23. Authentication and RAG Security

Authentication must happen before any RAG operation.

The following flow is mandatory:

```text
User
 ↓
Supabase Auth
 ↓
JWT
 ↓
FastAPI authentication
 ↓
Application identity
 ↓
Authorization
 ↓
Permission-aware retrieval
 ↓
Qdrant Cloud
 ↓
Authorized chunks
 ↓
Ollama
 ↓
Answer
```

This is a critical security invariant.

The LLM must never be asked to determine whether the user is allowed to see retrieved information.

---

# 24. Authentication Middleware

FastAPI should provide reusable authentication dependencies/middleware rather than duplicating authentication logic across endpoints.

Conceptually:

```text
require_authenticated_user()
```

can be used by:

```text
/api/chat
/api/documents
/api/users
/api/admin
```

The authentication component should produce a consistent authenticated-user context for downstream services.

This prevents individual endpoints from implementing different authentication behavior.

---

# 25. Public Endpoints

Only explicitly designated endpoints may be public.

Examples may include:

```text
GET /health
GET /ready
```

Authentication requirements for operational endpoints must be documented separately.

All enterprise data endpoints should require authentication unless explicitly justified.

---

# 26. Authentication Logging

Authentication-related events should be auditable without logging secrets.

Events may include:

- successful authentication
- failed authentication
- expired token
- invalid token
- inactive account rejection
- logout
- security-sensitive authentication changes
- MFA-related security events where enabled

Logs must never contain:

```text
passwords
access tokens
refresh tokens
service-role keys
JWT signing secrets
```

The audit architecture is defined separately in the security and audit documentation.

---

# 27. MFA Readiness

The architecture should remain compatible with Multi-Factor Authentication.

Supabase Auth supports MFA and exposes an authentication assurance level (`aal`) in JWT claims.

The platform can later introduce policies such as:

```text
Normal user
→ AAL1 accepted

Administrator
→ AAL2 required
```

This should be implemented as an authorization/security policy rather than embedded into individual application features.

MFA is therefore an architectural extension point, even if it is not enabled in the initial implementation.

---

# 28. Security Invariants

The following rules are mandatory.

### Invariant 1 — No custom password storage

The application must never store user passwords or password hashes.

### Invariant 2 — Never trust decoded JWTs

JWT claims must only be trusted after proper validation.

### Invariant 3 — Authentication precedes authorization

No authorization decision may be made for an unresolved identity.

### Invariant 4 — Authorization precedes retrieval

Permission checks must happen before protected enterprise content reaches the RAG pipeline.

### Invariant 5 — Unauthorized context never reaches the LLM

The generation model must only receive authorized context.

### Invariant 6 — Service credentials remain server-side

Privileged Supabase credentials must never reach the frontend.

### Invariant 7 — Client-side state is not authoritative

Frontend authentication or role state must never be the final security decision.

### Invariant 8 — Authentication failures stop execution

An unauthenticated request must not reach protected business logic.

---

# 29. Testing Strategy

Authentication must be tested independently and as part of integration tests.

## Unit Tests

Test:

- JWT parsing
- JWT validation
- expiration handling
- issuer validation
- audience validation
- missing claims
- authenticated-user construction
- inactive-user rejection

## Integration Tests

Test:

```text
Valid JWT
    → authenticated request
```

```text
Expired JWT
    → 401
```

```text
Invalid JWT
    → 401
```

```text
Missing JWT
    → 401
```

```text
Valid JWT + inactive profile
    → rejected
```

```text
Valid JWT + insufficient permission
    → 403
```

## Security Tests

Test that:

- forged JWTs are rejected
- modified JWT payloads are rejected
- service credentials are not exposed
- authentication bypass attempts fail
- protected endpoints cannot be called anonymously
- unauthorized users cannot reach RAG retrieval
- unauthorized chunks cannot reach generation

---

# 30. Configuration

Authentication configuration must be supplied through environment variables.

Example categories:

```text
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY
SUPABASE_JWT_ISSUER
SUPABASE_JWT_AUDIENCE
```

The exact variables will be finalized during environment configuration.

Secrets must never be committed to source control.

`.env.example` must contain placeholders only.

---

# 31. Authentication Request Lifecycle

The complete request lifecycle is:

```text
┌───────────────┐
│    Browser    │
└───────┬───────┘
        │
        │ Supabase Auth
        ▼
┌───────────────┐
│ Supabase Auth │
└───────┬───────┘
        │
        │ JWT
        ▼
┌───────────────┐
│    FastAPI    │
└───────┬───────┘
        │
        │ Validate JWT
        ▼
┌───────────────┐
│ Authenticated │
│     User      │
└───────┬───────┘
        │
        │ Resolve profile
        ▼
┌───────────────┐
│ Authorization │
└───────┬───────┘
        │
        │ Allowed?
        ▼
┌───────────────┐
│ Application   │
│   Service     │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ RAG / DB /    │
│ Other Service │
└───────────────┘
```

---

# 32. What Authentication Does Not Do

Authentication does **not**:

- determine document permissions
- determine department access
- determine RAG visibility
- filter Qdrant Cloud results
- decide which documents can be cited
- decide administrator privileges
- validate business permissions
- replace RLS
- replace application authorization

Those responsibilities belong to the authorization architecture.

---

# 33. Definition of Done

Authentication is considered complete when:

- [ ] Supabase Auth is configured
- [ ] Frontend authentication flow is implemented
- [ ] FastAPI protected endpoints require authentication
- [ ] JWTs are cryptographically validated
- [ ] JWT issuer and audience are validated
- [ ] JWT expiration is enforced
- [ ] `sub` is mapped to the application profile
- [ ] inactive accounts are rejected
- [ ] authentication failures return appropriate `401` responses
- [ ] authorization failures return appropriate `403` responses
- [ ] no application password hashes exist
- [ ] privileged Supabase credentials remain server-side
- [ ] authentication logic is centralized
- [ ] authentication events can be audited
- [ ] authentication unit tests pass
- [ ] authentication integration tests pass
- [ ] authentication security tests pass
- [ ] authentication occurs before authorization
- [ ] authorization occurs before RAG retrieval

---

# 34. Related Documentation

This document connects to:

- `docs/architecture/system.md`
- `docs/architecture/backend.md`
- `docs/architecture/data-model.md`
- `docs/architecture/integrations.md`
- `docs/security/security-architecture.md`
- `docs/security/authorization.md`
- `docs/security/threat-model.md`
- `docs/rag/retrieval.md`
- `docs/rag/generation.md`
- `docs/deployment/local-development.md`

---

# 35. Final Architecture Principle

The platform follows one fundamental authentication rule:

> **Supabase Auth establishes identity. FastAPI validates that identity. Application authorization determines access. RAG only operates on already-authorized data.**

Authentication is therefore the first security boundary, but it is **not the final authorization boundary**.

# Authentication

## 1. Purpose

This document defines authentication for the Supabase-based platform.

Authentication answers:

> Who are you?

Authorization answers:

> What are you allowed to access?

The two must not be collapsed into one step.

---

# 2. Authentication Flow

```text
Registration/login
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
profiles lookup
       ↓
application identity
```

Supabase Auth handles registration, login, password management, session management, JWT issuance, token refresh, and authentication lifecycle.

FastAPI validates the Supabase-issued JWT and resolves the matching `public.profiles` record.

---

# 3. Application Profile

Supabase-managed:

```text
auth.users
```

Application-managed:

```text
public.profiles
```

`profiles.id` references the corresponding Supabase Auth user ID.

`profiles` contains application data such as name, department, active status, and superuser flag. It must not contain authentication secrets.

---

# 4. Passwords and Sessions

Do not create custom password authentication.

Do not store plaintext passwords.

Do not store custom password credentials in application profile tables.

Supabase Auth owns password and session management.

---

# 5. Server and Client Boundaries

The frontend may use public Supabase configuration:

- Supabase URL
- Publishable key

The service-role or secret key must never be exposed to the browser, client-side Next.js code, public API responses, Git, logs, or frontend environment variables.

FastAPI may use privileged Supabase credentials only for trusted server-side operations.

---

# 6. Failure Behavior

Authentication failures must not reveal sensitive details.

Expired, invalid, or missing tokens fail closed.

An authenticated Supabase user without an active application profile must not receive application access.

---

# 7. Relationship to Authorization

Authentication does not grant document access by itself.

The required protected flow is:

```text
Authentication
      ↓
Identity
      ↓
Authorization
      ↓
Permission-aware retrieval
      ↓
Generation
```
