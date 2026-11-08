-- Module 11: restrict direct client access to document metadata
--
-- Document operations are authorized by FastAPI and executed with the
-- Supabase service-role client. RLS policies remain enabled and unchanged.

revoke all privileges on table public.documents
    from anon, authenticated;

grant select, insert, update on table public.documents
    to service_role;
