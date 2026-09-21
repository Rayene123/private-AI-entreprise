# Production Deployment

## 1. Purpose

This document defines the production deployment architecture and operational requirements.

---

# 2. Production Architecture

```text
                         Internet
                            │
                            ▼
                       HTTPS / TLS
                            │
                            ▼
                    ┌───────────────┐
                    │   Frontend    │
                    │   Next.js     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    FastAPI    │
                    │   Backend     │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
          Supabase       Qdrant Cloud        Ollama
          Postgres
          Storage
          Auth
```

---

# 3. HTTPS

All external traffic must use HTTPS.

HTTP should redirect to HTTPS where applicable.

---

# 4. Authentication

Supabase Auth manages user authentication.

FastAPI validates authenticated requests before processing protected operations.

---

# 5. Authorization

Every sensitive operation must pass backend authorization.

Examples:

```text
Document access
Document deletion
User administration
Role modification
Permission modification
Tool execution
```

---

# 6. Database

Supabase PostgreSQL is authoritative for relational state.

Production requirements:

- RLS configured
- Migrations applied
- Backups enabled
- Access restricted
- Service-role key protected

---

# 7. Storage

Enterprise documents must remain in private storage.

Public buckets should not contain confidential enterprise documents.

---

# 8. Qdrant Cloud

Production Qdrant Cloud must:

- Require authentication
- Use restricted network/API access where supported
- Have managed backups/snapshots configured where required
- Restrict write access
- Log index modifications where possible

Only ingestion/reindexing components should write to the index.

---

# 9. Ollama

Ollama should remain on the private network.

It should not be exposed directly to the Internet.

Only authorized backend components should communicate with it.

---

# 10. Secrets

Production secrets must be managed through the deployment environment or a dedicated secret-management system.

Examples:

```text
Supabase service key
Qdrant Cloud credentials
External API keys
Infrastructure credentials
```

Secrets should be rotated when necessary.

---

# 11. Monitoring

Monitor:

```text
API health
CPU
Memory
Disk
Qdrant Cloud
Ollama
Database
Storage
Request latency
Error rates
Security events
```

---

# 12. Alerting

Alert on:

- Authentication failures
- Authorization failures
- Service outages
- Excessive resource use
- Repeated prompt-injection detections
- Unexpected vector-index changes
- Storage failures
- Database failures
- Unusual retrieval patterns

---

# 13. Backups

Back up:

- PostgreSQL
- Documents
- Qdrant Cloud snapshots
- Critical configuration
- Audit records according to retention requirements

Test restoration regularly.

---

# 14. Disaster Recovery

Recovery should support:

```text
Supabase restored
       ↓
Documents available
       ↓
Qdrant Cloud rebuilt if necessary
       ↓
Application restored
       ↓
Security validation
       ↓
Service restored
```

Qdrant Cloud is a managed derived index and should therefore be rebuildable from authoritative source data.

---

# 15. Deployment Pipeline

Recommended:

```text
Git Push
   ↓
CI
   ↓
Lint
   ↓
Tests
   ↓
Security Tests
   ↓
Build Images
   ↓
Container Scan
   ↓
Deploy Staging
   ↓
Smoke Tests
   ↓
Production
```

---

# 16. Database Migration Safety

Before production migration:

1. Backup.
2. Test migration.
3. Run integration tests.
4. Apply migration.
5. Verify schema.
6. Verify authorization behavior.

Permission-related migrations require additional security testing.

---

# 17. Rollback

Every deployment should have a rollback strategy.

Application rollback:

```text
Previous image
      ↓
Redeploy
```

Database rollback should be handled carefully because schema changes may not always be safely reversible.

Prefer forward-compatible migrations.

---

# 18. Security Incident Response

When a security incident occurs:

```text
Detect
 ↓
Contain
 ↓
Investigate
 ↓
Eradicate
 ↓
Recover
 ↓
Validate
 ↓
Document
```

For a suspected RAG poisoning incident:

```text
Identify poisoned document
 ↓
Quarantine document
 ↓
Remove affected vectors
 ↓
Invalidate affected caches
 ↓
Identify affected responses/users
 ↓
Re-index trusted content
 ↓
Review logs
```

This follows the broader RAG security principle that incidents must be traceable across ingestion, retrieval, generation, and downstream actions.

---

# 19. Production Security Checklist

### Authentication

- [ ] HTTPS enabled
- [ ] Supabase Auth configured
- [ ] JWT validation active
- [ ] Session expiration configured

### Authorization

- [ ] Backend authorization active
- [ ] RLS configured
- [ ] Permission checks centralized
- [ ] Document authorization tested

### RAG

- [ ] Permission-aware retrieval
- [ ] Prompt-injection defenses
- [ ] Citation validation
- [ ] Retrieval limits
- [ ] Fail-closed behavior

### Infrastructure

- [ ] Qdrant Cloud private
- [ ] Ollama private
- [ ] Secrets protected
- [ ] Containers hardened
- [ ] Images scanned

### Operations

- [ ] Monitoring
- [ ] Alerting
- [ ] Backups
- [ ] Restore testing
- [ ] Incident response plan

---

# 20. Definition of Done

Production deployment is complete when:

- [ ] HTTPS is configured.
- [ ] Authentication works.
- [ ] Authorization works.
- [ ] RLS policies are tested.
- [ ] Storage is private.
- [ ] Qdrant Cloud is secured.
- [ ] Ollama is private.
- [ ] Secrets are protected.
- [ ] Monitoring exists.
- [ ] Alerts exist.
- [ ] Backups exist.
- [ ] Restore procedure has been tested.
- [ ] CI/CD is operational.
- [ ] Security tests pass.
- [ ] Incident response procedure exists.
- [ ] Production rollback procedure exists.
