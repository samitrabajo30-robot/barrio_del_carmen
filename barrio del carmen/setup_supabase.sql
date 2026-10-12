-- Ejecutar una sola vez en Supabase > SQL Editor. Ver README.md para habilitar el administrador.
create table if not exists public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.admins enable row level security;
create policy "admins can read their own authorization" on public.admins
  for select to authenticated using (user_id = (select auth.uid()));

create table if not exists public.site_content (
  key text primary key, value text not null default '', updated_at timestamptz not null default now()
);
alter table public.site_content enable row level security;
create policy "public can read site content" on public.site_content for select to anon, authenticated using (true);
create policy "admins can insert site content" on public.site_content for insert to authenticated
  with check (exists (select 1 from public.admins where user_id = (select auth.uid())));
create policy "admins can update site content" on public.site_content for update to authenticated
  using (exists (select 1 from public.admins where user_id = (select auth.uid())))
  with check (exists (select 1 from public.admins where user_id = (select auth.uid())));
insert into public.site_content(key, value) values
  ('intro', 'Este es un punto de encuentro para quienes viven y trabajan en el barrio. Queremos compartir información útil, celebrar lo que hacemos juntos y encontrar soluciones entre todos.'),
  ('history', 'La historia de Nuestra Señora del Carmen se sumará próximamente con el aporte de sus vecinos.'),
  ('hero_image', ''), ('extra_text', '') on conflict (key) do nothing;

create table if not exists public.complaints (
  id bigint generated always as identity primary key,
  problem_date date not null, problem_time time not null,
  zone text not null check (char_length(zone) between 2 and 100),
  topic text not null check (topic in ('Alumbrado','Calles','Residuos','Servicios','Otro')),
  description text not null check (char_length(description) between 10 and 1500),
  status text not null default 'recibida' check (status in ('recibida','en_gestion','resuelta')),
  created_at timestamptz not null default now()
);
alter table public.complaints enable row level security;
create policy "public can submit a complaint" on public.complaints for insert to anon, authenticated
  with check (status = 'recibida');
create policy "admins can read complaints" on public.complaints for select to authenticated
  using (exists (select 1 from public.admins where user_id = (select auth.uid())));
create policy "admins can update complaint status" on public.complaints for update to authenticated
  using (exists (select 1 from public.admins where user_id = (select auth.uid())))
  with check (exists (select 1 from public.admins where user_id = (select auth.uid())));

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('public-assets', 'public-assets', true, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update set public = true, file_size_limit = 5242880,
  allowed_mime_types = array['image/jpeg','image/png','image/webp'];
create policy "public can view neighborhood images" on storage.objects for select to anon, authenticated
  using (bucket_id = 'public-assets');
create policy "admins can upload neighborhood images" on storage.objects for insert to authenticated
  with check (bucket_id = 'public-assets' and exists (select 1 from public.admins where user_id = (select auth.uid())));
create policy "admins can replace neighborhood images" on storage.objects for update to authenticated
  using (bucket_id = 'public-assets' and exists (select 1 from public.admins where user_id = (select auth.uid())))
  with check (bucket_id = 'public-assets' and exists (select 1 from public.admins where user_id = (select auth.uid())));
