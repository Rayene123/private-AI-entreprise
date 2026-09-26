-- Module 6: Secure Document Storage & File Access
--
-- This migration provisions the private Supabase Storage bucket used to
-- hold enterprise document files, and adds defense-in-depth Row Level
-- Security policies on storage.objects for that bucket.
--
-- The application does NOT rely on these storage.objects policies for
-- authorization. All upload/download requests are authorized in the
-- FastAPI backend (JWT -> RBAC -> document-level access) before the
-- backend's service-role Supabase client ever touches storage, and the
-- service role bypasses RLS entirely. These policies exist only so that a
-- misconfigured or leaked non-service credential cannot read or write
-- enterprise document objects directly.
--
-- Bucket creation via SQL requires appropriate privileges on the storage
-- schema. If this statement cannot be applied in your Supabase project
-- (for example, via the SQL editor without sufficient privileges), create
-- the bucket manually instead:
--
--   Dashboard -> Storage -> New bucket
--     name:   enterprise-documents
--     public: false (must remain private)
--
-- Do not make this bucket public, and do not weaken these policies to
-- work around permission errors while creating it.

insert into storage.buckets (id, name, public)
values ('enterprise-documents', 'enterprise-documents', false)
on conflict (id) do update
set public = false;

alter table storage.objects enable row level security;

drop policy if exists "enterprise_documents_no_direct_access" on storage.objects;
create policy "enterprise_documents_no_direct_access"
on storage.objects
for all
to authenticated, anon
using (bucket_id <> 'enterprise-documents')
with check (bucket_id <> 'enterprise-documents');