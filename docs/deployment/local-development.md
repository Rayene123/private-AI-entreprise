# Local Development

## 1. Purpose

This document describes how to run the platform locally.

---

# 2. Architecture

Local development uses:

```text
Next.js
FastAPI
Qdrant Cloud
Ollama
     │
     └── Supabase
```

Supabase PostgreSQL is not duplicated inside the local Docker stack by default.

---

# 3. Prerequisites

Install:

- Git
- Docker
- Docker Compose
- Node.js
- Python
- Ollama

Create a Supabase project.

---

# 4. Environment Configuration

Create:

```text
.env
```

from:

```text
.env.example
```

Never commit `.env`.

---

# 5. Backend

Create a Python environment.

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run FastAPI:

```bash
uvicorn app.main:app --reload
```

---

# 6. Frontend

Install dependencies:

```bash
cd frontend
npm install
```

Run:

```bash
npm run dev
```

---

# 7. Qdrant Cloud

Start Qdrant Cloud using Docker.

The development environment should expose Qdrant Cloud only as required for local development.

---

# 8. Ollama

Install the required local model.

Verify:

```bash
ollama list
```

The model configuration must match the backend configuration.

---

# 9. Supabase

Configure:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
```

The service-role key must only exist in the backend environment.

---

# 10. Database Migrations

Database changes should be version-controlled.

Use the selected Supabase migration workflow.

Never manually modify production schema without a corresponding migration.

---

# 11. Development Workflow

```text
Create branch
 ↓
Implement module
 ↓
Run unit tests
 ↓
Run integration tests
 ↓
Run security tests
 ↓
Update documentation
 ↓
Commit
```

---

# 12. Definition of Done

- [ ] Supabase project configured.
- [ ] Backend runs.
- [ ] Frontend runs.
- [ ] Qdrant Cloud runs.
- [ ] Ollama runs.
- [ ] Environment variables documented.
- [ ] Database migrations work.
- [ ] Basic tests run.
- [ ] No secrets are committed.
