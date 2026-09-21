# Docker Deployment

## 1. Purpose

This document defines containerization for the platform.

---

# 2. Services

The default Docker architecture contains:

```text
frontend
backend
ollama
```

Supabase and Qdrant Cloud remain external managed services in the default architecture.

---

# 3. Docker Compose

Conceptually:

```text
docker-compose.yml
│
├── frontend
├── backend
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

# 6. Qdrant Cloud

Qdrant Cloud is not run as a default Docker container. The backend connects to Qdrant Cloud through configured endpoint and API-key settings.

Qdrant Cloud should:

- Require authentication where applicable
- Restrict network/API access where supported
- Be accessible only to authorized backend components
- Be treated as a derived index that can be rebuilt

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
backend → ollama
backend → Supabase
backend → Qdrant Cloud
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
Qdrant Cloud → managed health/API check
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
Ollama model data
```

Qdrant Cloud persistence and backups are managed by Qdrant Cloud configuration. Supabase data is managed separately.

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
