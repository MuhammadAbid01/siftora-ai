-- Phase 4: outreach drafts, approvals, suppression, and sender fields.
-- See specs/phase-4-outreach.md for design rationale.

alter table public.campaigns add column sender_name text;
alter table public.campaigns add column sender_email text;

create table public.outreach_drafts (
  id uuid primary key default gen_random_uuid (),
  lead_id uuid not null references public.leads (id) on delete cascade,
  channel text not null check (channel in ('email', 'linkedin')),
  subject text not null,
  body text not null,
  version integer not null check (version >= 1),
  quality_status text not null check (quality_status in ('passed', 'needs_review')),
  evidence_refs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (lead_id, channel, version)
);

create index outreach_drafts_lead_id_idx on public.outreach_drafts (lead_id);

alter table public.outreach_drafts enable row level security;

create policy "outreach_drafts_select_own" on public.outreach_drafts
  for select
  using (
    exists (
      select 1 from public.leads
      join public.campaigns on campaigns.id = leads.campaign_id
      where leads.id = outreach_drafts.lead_id
        and campaigns.user_id = auth.uid ()
    )
  );

create trigger outreach_drafts_set_updated_at
  before update on public.outreach_drafts
  for each row
  execute function public.set_updated_at ();

create table public.approvals (
  id uuid primary key default gen_random_uuid (),
  draft_id uuid not null unique references public.outreach_drafts (id) on delete cascade,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'rejected')),
  reviewer_id uuid references auth.users (id),
  decided_at timestamptz,
  edited boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index approvals_draft_id_idx on public.approvals (draft_id);

alter table public.approvals enable row level security;

create policy "approvals_select_own" on public.approvals
  for select
  using (
    exists (
      select 1 from public.outreach_drafts
      join public.leads on leads.id = outreach_drafts.lead_id
      join public.campaigns on campaigns.id = leads.campaign_id
      where outreach_drafts.id = approvals.draft_id
        and campaigns.user_id = auth.uid ()
    )
  );

create trigger approvals_set_updated_at
  before update on public.approvals
  for each row
  execute function public.set_updated_at ();

create table public.suppression_entries (
  id uuid primary key default gen_random_uuid (),
  user_id uuid not null references auth.users (id) on delete cascade,
  domain text not null,
  reason text,
  created_at timestamptz not null default now(),
  unique (user_id, domain)
);

create index suppression_entries_user_id_idx on public.suppression_entries (user_id);

alter table public.suppression_entries enable row level security;

create policy "suppression_entries_select_own" on public.suppression_entries
  for select
  using (auth.uid () = user_id);

create policy "suppression_entries_insert_own" on public.suppression_entries
  for insert
  with check (auth.uid () = user_id);

create policy "suppression_entries_delete_own" on public.suppression_entries
  for delete
  using (auth.uid () = user_id);
