-- Module 5: Document Management & Document-Level Access Control

create table if not exists public.documents (
    id uuid primary key default extensions.gen_random_uuid(),
    owner_id uuid not null references public.profiles(id) on delete restrict,
    department_id uuid null references public.departments(id) on delete set null,
    title text not null,
    description text null,
    original_filename text null,
    storage_path text null,
    mime_type text null,
    file_size_bytes bigint null,
    status text not null default 'active',
    access_level text not null default 'department',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint documents_status_check
        check (status in ('active', 'archived')),
    constraint documents_access_level_check
        check (access_level in ('private', 'department', 'organization')),
    constraint documents_file_size_bytes_check
        check (file_size_bytes is null or file_size_bytes >= 0)
);

create table if not exists public.document_user_access (
    document_id uuid not null references public.documents(id) on delete cascade,
    user_id uuid not null references public.profiles(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (document_id, user_id)
);

create index if not exists idx_documents_owner_id
    on public.documents(owner_id);

create index if not exists idx_documents_department_id
    on public.documents(department_id);

create index if not exists idx_documents_status
    on public.documents(status);

create index if not exists idx_documents_access_level
    on public.documents(access_level);

create index if not exists idx_document_user_access_user_id
    on public.document_user_access(user_id);

drop trigger if exists set_documents_updated_at on public.documents;
create trigger set_documents_updated_at
before update on public.documents
for each row
execute function public.set_updated_at();

alter table public.documents enable row level security;
alter table public.document_user_access enable row level security;

drop policy if exists "documents_authenticated_read_defense" on public.documents;
create policy "documents_authenticated_read_defense"
on public.documents
for select
to authenticated
using (
    owner_id = auth.uid()
    or access_level = 'organization'
    or (
        access_level = 'department'
        and department_id in (
            select p.department_id
            from public.profiles p
            where p.id = auth.uid()
        )
    )
    or exists (
        select 1
        from public.document_user_access dua
        where dua.document_id = documents.id
          and dua.user_id = auth.uid()
    )
);

drop policy if exists "documents_authenticated_insert_own" on public.documents;
create policy "documents_authenticated_insert_own"
on public.documents
for insert
to authenticated
with check (owner_id = auth.uid());

drop policy if exists "documents_authenticated_update_own_without_owner_change" on public.documents;
create policy "documents_authenticated_update_own_without_owner_change"
on public.documents
for update
to authenticated
using (owner_id = auth.uid())
with check (owner_id = auth.uid());

drop policy if exists "document_user_access_select_own" on public.document_user_access;
create policy "document_user_access_select_own"
on public.document_user_access
for select
to authenticated
using (user_id = auth.uid());

revoke insert, update, delete on public.document_user_access from authenticated;
revoke delete on public.documents from authenticated;
grant select, insert, update on public.documents to authenticated;
grant select on public.document_user_access to authenticated;
