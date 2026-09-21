# Coding Standards

## 1. Purpose

This document defines coding standards for the project.

The goals are:

- Readability
- Maintainability
- Security
- Testability
- Modularity
- Consistency

---

# 2. General Principles

Follow:

- Single responsibility
- Explicit dependencies
- Small modules
- Clear interfaces
- Composition over unnecessary inheritance
- Fail-fast validation
- Type safety
- Secure defaults

Avoid:

- Global mutable state
- Hidden dependencies
- Large monolithic services
- Duplicate authorization logic
- Hardcoded secrets
- Dead code

---

# 3. Python

Use:

- Python 3.x
- Type hints
- Pydantic
- FastAPI conventions
- `ruff` or equivalent linting
- `pytest`

Example:

```python
def can_access_document(
    user_id: UUID,
    document_id: UUID,
) -> bool:
    ...
```

Avoid untyped public functions.

---

# 4. FastAPI

Keep API routes thin.

Preferred:

```text
API route
   ↓
Schema validation
   ↓
Service
   ↓
Repository / integration
```

Avoid putting complex business logic directly inside route functions.

---

# 5. Services

Services contain application/business logic.

Examples:

```text
auth_service.py
permission_service.py
document_service.py
audit_service.py
```

Services should not depend unnecessarily on HTTP-specific objects.

---

# 6. Authorization

Authorization must be centralized.

Do not implement:

```python
if user.role == "admin":
```

throughout the application.

Prefer a permission abstraction.

Example:

```text
permission_service.has_permission(...)
```

This prevents authorization logic from becoming inconsistent.

---

# 7. RAG Modules

RAG components should expose interfaces rather than tightly coupling the entire pipeline.

Example:

```python
class Retriever(Protocol):
    async def retrieve(...):
        ...
```

This allows different implementations to be tested independently.

---

# 8. Error Handling

Use explicit application exceptions.

Examples:

```text
AuthenticationError
AuthorizationError
DocumentNotFoundError
RetrievalError
ValidationError
```

Do not expose stack traces to users.

---

# 9. Logging

Logs should be structured.

Include:

- Timestamp
- Log level
- Component
- Request ID
- User ID where appropriate
- Event type

Never log:

- Passwords
- Tokens
- API keys
- Secrets
- Full sensitive documents

---

# 10. TypeScript

Use strict TypeScript.

Avoid:

```typescript
any;
```

unless there is a documented reason.

Prefer explicit interfaces/types.

---

# 11. React

Components should have one clear responsibility.

Prefer:

```text
ChatMessage
Citation
ChatInput
DocumentCard
PermissionGate
```

over a single massive page component.

---

# 12. Naming

Use descriptive names.

Python:

```text
snake_case
```

TypeScript:

```text
camelCase
```

React components:

```text
PascalCase
```

Constants:

```text
UPPER_SNAKE_CASE
```

---

# 13. Environment Variables

All configuration must come from environment/configuration.

Never:

```python
API_KEY = "secret"
```

Use configuration objects instead.

---

# 14. Security

Every new feature must answer:

- What identity does it operate under?
- What permission is required?
- What data can it access?
- Can the input be attacker-controlled?
- Can the feature expose sensitive information?
- Does it create a new trust boundary?
- Does it require audit logging?

---

# 15. Testing

New functionality should include tests.

Critical security behavior must include negative tests.

Example:

```text
Authorized user → succeeds
Unauthorized user → denied
Missing permission → denied
Invalid input → rejected
```

---

# 16. Git

Use focused commits.

Examples:

```text
feat(auth): add Supabase JWT validation
feat(rag): add hybrid retrieval
fix(authz): prevent cross-department retrieval
test(rag): add permission leakage tests
docs(security): update threat model
```

---

# 17. Pull Requests

Each PR should explain:

- What changed
- Why
- Security impact
- Tests performed
- Database changes
- Migration requirements
- Environment changes

---

# 18. Definition of Done

Code is complete when:

- [ ] It follows project structure.
- [ ] Types are defined.
- [ ] Validation exists.
- [ ] Authorization is explicit.
- [ ] Errors are handled.
- [ ] Logging is safe.
- [ ] Tests exist.
- [ ] Security implications are reviewed.
- [ ] Documentation is updated where necessary.
