# Corporate Reference Dataset

## Purpose

This collection contains six publicly sourced corporate-policy reference
documents for dataset inspection and controlled evaluation of the Private
Enterprise AI Platform. They are reference materials for a simulated
enterprise knowledge base, not documents belonging to one real company.

## Public external sources vs synthetic internal documents

The inventory marks these PDFs as `source_type=public_external`. Their rules,
dates, terminology, and responsibilities belong to their named source
organizations. Synthetic internal-company documents, if added later, must be
identified separately and must not be mixed with these public references.

## Organization

- `raw/hr/`: human-resources and remote-work material
- `raw/it/`: acceptable-use and BYOD material
- `raw/finance/`: travel and expense material
- `metadata/`: inventory CSV and inspection report
- `evaluation/`: evaluation artifacts, if created later

## Metadata conventions

`metadata/documents.csv` uses stable IDs such as `CORP-HR-001`, preserves the
actual local filename, records the repository-relative path, and leaves
unknown dates or URLs empty. The initial collection uses
`access_level=organization`, `source_type=public_external`, and
`ingestion_status=not_ingested`.

## Provenance

Source organization and document dates must remain attached to every document
and, later, to every derived chunk and citation. Policies from different
institutions can overlap while imposing different requirements.

For example, the Temple and Suffolk travel policies are not a unified travel
policy; the King's acceptable-use policy and BYOD procedure have different
scopes; and the handbook and remote-work policy come from different
institutions. Do not merge them or describe them as one company's rules.

## Ingestion workflow

This task only inventories the PDFs. The planned later workflow is:

1. Review provenance and refresh dates.
2. Validate PDF extraction and table preservation.
3. Create documents through the application workflow.
4. Upload files through private Storage.
5. Run Module 7 parsing, Markdown conversion, and chunking.
6. Run Module 8 embeddings and Qdrant indexing.
7. Verify Module 9 authorization and Module 10 citation behavior.

## Controlled ingestion

After applying the provenance migration
`backend/app/db/migrations/004_module11_dataset_provenance.sql`, run
`backend/scripts/ingest_corporate_dataset.py` with an existing authorized
owner selected through `DATASET_INGESTION_OWNER_ID`. The runner uses the
application document, private Storage, ingestion, embedding, and indexing
services. It records source metadata and SHA-256 hashes, skips identical
already-indexed documents, and stops rather than overwriting a changed source.

The six records are persistent reference data, not disposable live-verification
fixtures. The runner does not delete or archive records automatically.

No PDF was uploaded, embedded, chunked, or sent to Supabase or Qdrant for this
inventory task. The raw directory remains ignored by Git and original PDFs
must not be modified, moved, or deleted.
