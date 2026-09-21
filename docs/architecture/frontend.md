# Frontend Architecture

## 1. Purpose

This document defines the architecture of the Next.js frontend for the Private Enterprise AI Platform.

The frontend is responsible for:

- User interface
- Authentication experience
- Chat interface
- Document management interface
- Administrative interface
- Client-side state
- API communication
- User-facing error handling
- Permission-aware UI rendering

The frontend is **not** a security boundary.

All sensitive authorization decisions must be enforced by the FastAPI backend.

---

# 2. Technology Stack

The frontend uses:

- Next.js
- TypeScript
- React
- Supabase Auth
- Tailwind CSS or the selected UI system
- Fetch or an equivalent HTTP client
- React hooks
- Server/client components according to Next.js requirements

---

# 3. Directory Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── login/
│   │   ├── chat/
│   │   ├── documents/
│   │   ├── admin/
│   │   └── settings/
│   │
│   ├── components/
│   │   ├── ui/
│   │   ├── layout/
│   │   ├── chat/
│   │   ├── documents/
│   │   └── admin/
│   │
│   ├── features/
│   │   ├── auth/
│   │   ├── chat/
│   │   ├── documents/
│   │   └── admin/
│   │
│   ├── lib/
│   │   ├── supabase/
│   │   ├── api/
│   │   ├── auth/
│   │   └── utils/
│   │
│   └── hooks/
│       ├── use-auth.ts
│       ├── use-user.ts
│       └── use-permissions.ts
│
├── public/
├── package.json
├── Dockerfile
└── .dockerignore
```

---

# 4. Application Layers

The frontend is divided into:

```text
Pages / Routes
      ↓
Feature Components
      ↓
Reusable Components
      ↓
Hooks
      ↓
API / Supabase Client
```

Business logic should not be duplicated across pages.

---

# 5. Authentication

Supabase Auth manages:

- Sign in
- Sign out
- Session management
- Password operations
- Authentication state

The frontend should obtain the authenticated session and use its access token when communicating with FastAPI.

The frontend must never:

- Store passwords manually
- Implement its own authentication protocol
- Store service-role keys
- Store backend secrets
- Decide that a user is authorized for a sensitive operation

Authentication and authorization are separate concerns.

---

# 6. API Communication

All protected backend requests follow:

```text
Frontend
   ↓
Supabase Session
   ↓
Access Token
   ↓
Authorization: Bearer <token>
   ↓
FastAPI
```

API access should be centralized.

Example conceptual interface:

```text
apiClient.get()
apiClient.post()
apiClient.delete()
```

Individual components should not manually construct authorization headers repeatedly.

---

# 7. Permission-Aware UI

The frontend may hide UI elements that the current user cannot use.

Example:

```text
User without documents.delete
    ↓
Do not display Delete button
```

However:

```text
Hidden UI ≠ authorization
```

A malicious user can manually call the API.

FastAPI must independently verify every permission.

---

# 8. Chat Interface

The chat feature should support:

- User messages
- Assistant responses
- Streaming where supported
- Citations
- Source documents
- Loading states
- Error states
- Empty states
- Conversation history
- Retrieval metadata where appropriate

Example:

```text
User question
      ↓
FastAPI
      ↓
Secure RAG
      ↓
Response
      ↓
Citations
      ↓
Chat UI
```

The frontend should not independently retrieve enterprise documents to construct the model context.

---

# 9. Document Interface

Users may see:

- Documents they are authorized to access
- Metadata
- Classification
- Department
- Owner
- Upload status
- Processing status
- Available actions

The UI should never assume that a document is accessible simply because its ID is known.

The backend remains authoritative.

---

# 10. Administrative Interface

Administrative functionality should be isolated under `/admin`.

Potential sections:

```text
/admin/users
/admin/roles
/admin/permissions
/admin/departments
/admin/documents
/admin/audit
/admin/system
```

The frontend should request the required permissions from the backend rather than hardcoding administrative status as the final authority.

---

# 11. Error Handling

API errors should be converted into safe user-facing messages.

Examples:

```text
401 → Session expired
403 → You do not have permission
404 → Resource not found
422 → Invalid request
429 → Too many requests
500 → Internal server error
```

Backend implementation details must not be exposed to users.

---

# 12. Security Rules

The frontend must never contain:

- Supabase service-role key
- Qdrant Cloud credentials
- Ollama administrative credentials
- Database credentials
- Private API keys
- Internal service secrets

Only browser-safe configuration may be exposed.

---

# 13. State Management

State should be divided into:

### Authentication State

```text
session
user
profile
permissions
```

### Chat State

```text
messages
conversation
loading
streaming
citations
errors
```

### Document State

```text
documents
filters
pagination
upload state
processing state
```

### Administrative State

```text
users
roles
permissions
audit records
```

State should not contain unnecessary sensitive data.

---

# 14. Performance

The frontend should:

- Paginate large datasets
- Avoid unnecessary API requests
- Use loading boundaries
- Stream chat responses where appropriate
- Avoid rendering extremely large document lists
- Cache only data that is safe to cache

Sensitive responses should not be placed in shared caches without permission-aware isolation.

---

# 15. Accessibility

The frontend should provide:

- Keyboard navigation
- Accessible labels
- Semantic HTML
- Screen-reader support
- Visible focus states
- Accessible error messages
- Appropriate contrast
- Accessible loading states

---

# 16. Testing

Frontend tests should cover:

- Authentication states
- Permission-aware rendering
- Chat interactions
- Citation rendering
- Document management
- Admin UI
- API error handling
- Unauthorized UI states

Security tests must still be performed against the backend independently.

---

# 17. Definition of Done

- [ ] Next.js application is structured by feature.
- [ ] Supabase Auth integration exists.
- [ ] API client is centralized.
- [ ] Protected API requests include authentication.
- [ ] Permission-aware UI exists.
- [ ] Frontend does not contain server secrets.
- [ ] Chat interface supports citations.
- [ ] Document interface exists.
- [ ] Admin interface is isolated.
- [ ] API errors are handled safely.
- [ ] Sensitive data is not unnecessarily cached.
- [ ] Accessibility basics are implemented.
- [ ] Frontend tests cover critical flows.
