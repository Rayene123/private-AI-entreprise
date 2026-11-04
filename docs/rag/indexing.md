# Vector Indexing

Module 8 treats Qdrant as a derived, rebuildable index. PostgreSQL document
metadata and Supabase Storage remain authoritative.

## Pipeline

```text
Authorized document
  -> Module 7 canonical chunks
  -> Ollama embedding batches
  -> Qdrant collection upsert
```

The default provider is Ollama with `nomic-embed-text` and a configured
dimension of 768. The provider and dimension are configuration-driven; the
embedding response is validated before any point is written.

Qdrant uses a configured collection with cosine distance. Missing collections
are created, while an existing collection with a different dimension or
distance fails safely instead of being recreated.

## Payload and IDs

Each point contains `document_id`, `chunk_id`, `owner_id`, `department_id`,
`access_level`, `document_status`, `chunk_index`, `source_hash`,
`source_filename`, `page_number`, `content`, `embedding_model`, and
`embedding_dimension`.

The Qdrant point ID is a deterministic UUID5 derived from the existing Module
7 deterministic chunk ID. Re-indexing the same source upserts the same points.
After replacement upsert succeeds, points for the document with an older
source hash are removed. A failed embedding or upsert does not report success.

Qdrant metadata supports future authorization filters but is never treated as
the authorization boundary. Every indexing request first uses the existing
document authorization and Storage ingestion flow.

## Local setup

```powershell
ollama pull nomic-embed-text
$env:EMBEDDING_URL = "http://localhost:11434"
$env:EMBEDDING_MODEL = "nomic-embed-text"
$env:EMBEDDING_DIMENSION = "768"
docker run --name private-ai-qdrant -p 6333:6333 qdrant/qdrant
$env:QDRANT_URL = "http://localhost:6333"
$env:QDRANT_COLLECTION_NAME = "enterprise_documents"
```

`QDRANT_API_KEY` is optional for local Qdrant and must remain backend-only.
Vectors are not returned by the API.

## Live verification

The disposable live verifier uses synthetic data and the configured Ollama
and Qdrant services. On 2026-11-04 it passed 5 checks covering real embedding
generation, collection configuration, indexing, deterministic re-indexing,
and cleanup. Temporary Supabase and Qdrant resources were removed by the
verifier's `finally` cleanup path.
