# Corporate dataset ingestion report

## Status

Controlled ingestion is **deferred**. The implementation and local
validation are complete, but the live Supabase health check failed before any
document or Storage operation was attempted.

The required migration
`backend/app/db/migrations/004_module11_dataset_provenance.sql` must also be
applied before ingestion. The runner requires an explicitly selected existing
owner through `DATASET_INGESTION_OWNER_ID`; no owner was selected during this
attempt.

## Local preflight

- Inventory rows validated: 6
- Source PDFs found: 6
- Recorded file sizes validated: 6
- Source files modified: no
- Embeddings or Qdrant writes attempted: no
- Supabase connectivity: failed (`IntegrationUnavailableError` from the
  health check; no credentials or response body are recorded here)
- Temporary resources created: none
- Cleanup required: no

## Intended workflow

After the migration is applied and an authorized owner is selected, run
`backend/scripts/ingest_corporate_dataset.py`. It will create or resume the
six records through the existing application services, preserve provenance
and source hashes in `documents.source_metadata`, index through the existing
embedding/Qdrant orchestration, and write per-document results here.

The runner refuses a changed source hash for an existing dataset ID and does
not automatically delete or archive any record.
