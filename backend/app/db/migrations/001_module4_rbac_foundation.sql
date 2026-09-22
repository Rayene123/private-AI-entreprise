-- Module 4: User Profiles & RBAC Foundation

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.departments (
    id uuid primary key default extensions.gen_random_uuid(),
    name text unique not null,
    description text null,
    created_at timestamptz not null default now()
);

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    display_name text null,
    department_id uuid null references public.departments(id) on delete set null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.roles (
    id uuid primary key,
    name text unique not null,
    description text null,
    created_at timestamptz not null default now()
);

create table if not exists public.permissions (
    id uuid primary key,
    name text unique not null,
    description text null,
    created_at timestamptz not null default now()
);

create table if not exists public.user_roles (
    user_id uuid not null references public.profiles(id) on delete cascade,
    role_id uuid not null references public.roles(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (user_id, role_id)
);

create table if not exists public.role_permissions (
    role_id uuid not null references public.roles(id) on delete cascade,
    permission_id uuid not null references public.permissions(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (role_id, permission_id)
);

create index if not exists idx_profiles_department_id
    on public.profiles(department_id);

create index if not exists idx_user_roles_role_id
    on public.user_roles(role_id);

create index if not exists idx_role_permissions_permission_id
    on public.role_permissions(permission_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

insert into public.roles (id, name, description)
values
    ('00000000-0000-0000-0000-000000000001', 'admin', 'Application administrator'),
    ('00000000-0000-0000-0000-000000000002', 'manager', 'Team or department manager'),
    ('00000000-0000-0000-0000-000000000003', 'employee', 'Default application user')
on conflict (name) do update
set description = excluded.description;

insert into public.permissions (id, name, description)
values
    ('10000000-0000-0000-0000-000000000001', 'profile.read', 'Read own application profile'),
    ('10000000-0000-0000-0000-000000000002', 'profile.update', 'Update allowed own profile fields'),
    ('10000000-0000-0000-0000-000000000003', 'users.read', 'Read user directory information'),
    ('10000000-0000-0000-0000-000000000004', 'users.manage', 'Manage users and privileged user attributes'),
    ('10000000-0000-0000-0000-000000000005', 'documents.read', 'Read authorized documents'),
    ('10000000-0000-0000-0000-000000000006', 'documents.create', 'Create documents'),
    ('10000000-0000-0000-0000-000000000007', 'documents.update', 'Update authorized documents'),
    ('10000000-0000-0000-0000-000000000008', 'documents.delete', 'Delete authorized documents'),
    ('10000000-0000-0000-0000-000000000009', 'chat.use', 'Use chat features')
on conflict (name) do update
set description = excluded.description;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
cross join public.permissions p
where r.name = 'admin'
on conflict do nothing;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.name in (
    'profile.read',
    'profile.update',
    'users.read',
    'documents.read',
    'documents.create',
    'documents.update',
    'chat.use'
)
where r.name = 'manager'
on conflict do nothing;

insert into public.role_permissions (role_id, permission_id)
select r.id, p.id
from public.roles r
join public.permissions p on p.name in (
    'profile.read',
    'profile.update',
    'documents.read',
    'chat.use'
)
where r.name = 'employee'
on conflict do nothing;

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    employee_role_id uuid;
begin
    insert into public.profiles (id, display_name)
    values (
        new.id,
        coalesce(new.raw_user_meta_data ->> 'display_name', new.raw_user_meta_data ->> 'name')
    )
    on conflict (id) do nothing;

    select id into employee_role_id
    from public.roles
    where name = 'employee';

    if employee_role_id is not null then
        insert into public.user_roles (user_id, role_id)
        values (new.id, employee_role_id)
        on conflict do nothing;
    end if;

    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_auth_user();

alter table public.profiles enable row level security;
alter table public.departments enable row level security;
alter table public.roles enable row level security;
alter table public.permissions enable row level security;
alter table public.user_roles enable row level security;
alter table public.role_permissions enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles
for select
to authenticated
using (id = auth.uid());

drop policy if exists "profiles_update_own_basic_fields" on public.profiles;
create policy "profiles_update_own_basic_fields"
on public.profiles
for update
to authenticated
using (id = auth.uid())
with check (id = auth.uid());

revoke insert, update, delete on public.profiles from authenticated;
grant update (display_name) on public.profiles to authenticated;

revoke insert, update, delete on public.departments from authenticated;
revoke insert, update, delete on public.roles from authenticated;
revoke insert, update, delete on public.permissions from authenticated;
revoke insert, update, delete on public.user_roles from authenticated;
revoke insert, update, delete on public.role_permissions from authenticated;
