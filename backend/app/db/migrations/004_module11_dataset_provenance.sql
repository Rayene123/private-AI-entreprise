-- Module 11: provenance for controlled public-reference ingestion

alter table public.documents
    add column if not exists source_metadata jsonb null;

create index if not exists idx_documents_source_dataset_id
    on public.documents ((source_metadata->>'dataset_id'));
