# Docker Deployment

## 1. Purpose

This document defines containerization for the platform.

---

# 2. Services

The default Docker architecture contains:

```text
frontend
backend
qdrant
ollama
```

Supabase remains an external service in the default architecture.

---

# 3. Docker Compose

Conceptually:

```text
docker-compose.yml
│
├── frontend
├── backend
├── qdrant
└── ollama
```

---

# 4. Backend Container

Responsibilities:

- FastAPI
- RAG pipeline
- Authentication validation
- Authorization
- Business logic

The backend should run as a non-root user where practical.

---

# 5. Frontend Container

Responsibilities:

- Next.js
- Static assets
- Server-side rendering where applicable

The container should contain only required production dependencies.

---

# 6. Qdrant Cloud Container

Qdrant Cloud should:

- Use persistent storage
- Require authentication where applicable
- Not be unnecessarily exposed publicly
- Be accessible only to authorized application components

---

# 7. Ollama Container

Ollama should:

- Remain internal
- Not expose model administration publicly
- Use controlled model storage
- Have appropriate CPU/GPU resources

---

# 8. Networking

Internal communication should use the Docker network.

Example:

```text
frontend → backend
backend → qdrant
backend → ollama
backend → Supabase
```

The frontend should not directly communicate with Qdrant Cloud or Ollama.

---

# 9. Secrets

Secrets must be injected at runtime.

Do not place them in:

```text
Dockerfile
docker-compose.yml
source code
```

unless they are explicitly non-sensitive configuration values.

---

# 10. Resource Limits

Set reasonable limits for:

- CPU
- Memory
- Container processes
- Request size

AI workloads should be monitored for resource exhaustion.

---

# 11. Health Checks

Each service should expose an appropriate health mechanism.

Example:

```text
backend → /health
qdrant → health endpoint
frontend → application health
```

---

# 12. Image Security

Use:

- Minimal base images
- Versioned images
- Regular updates
- Dependency scanning

Avoid unnecessary packages.

---

# 13. Persistent Volumes

Persistent data may include:

```text
Qdrant Cloud data
Ollama model data
```

The persistence strategy must be documented.

Supabase data is managed separately.

---

# 14. Production Difference

Production should additionally use:

- HTTPS
- Restricted networking
- Secret management
- Monitoring
- Backups
- Resource limits
- Strong authentication
- Image scanning

---

# 15. Definition of Done

- [ ] Dockerfiles exist.
- [ ] Compose configuration exists.
- [ ] Services communicate through internal networking.
- [ ] Secrets are not baked into images.
- [ ] Health checks exist.
- [ ] Persistent data is configured.
- [ ] Resource limits are considered.
- [ ] Images are scanned.
- [ ] Production differences are documented.
