-- Phase 2: campaigns + campaign_icp, RLS, and updated_at triggers.
-- See specs/phase-2-campaigns.md for design rationale.

create table public.campaigns (
  id uuid primary key default gen_random_uuid (),
  user_id uuid not null references auth.users (id) on delete cascade,
  brief text not null,
  offer text,
  target_lead_count integer not null default 20
    check (target_lead_count between 1 and 200),
  status text not null default 'draft'
    check (status in ('draft', 'awaiting_plan_approval', 'plan_approved', 'queued')),
  search_plan jsonb,
  score_weights jsonb not null default '{
    "industry_fit": 20, "geography_fit": 10, "company_size_fit": 10,
    "pain_point_evidence": 20, "buying_signal": 15, "contact_relevance": 10,
    "recency": 10, "evidence_completeness": 5
  }'::jsonb,
  score_threshold_qualified integer not null default 75
    check (score_threshold_qualified between 0 and 100),
  score_threshold_needs_review integer not null default 55
    check (score_threshold_needs_review between 0 and 100),
  limit_max_queries integer not null default 20
    check (limit_max_queries between 1 and 100),
  limit_max_pages_per_company integer not null default 5
    check (limit_max_pages_per_company between 1 and 20),
  limit_max_retries integer not null default 2
    check (limit_max_retries between 0 and 5),
  limit_max_cost_usd numeric(10, 2) not null default 5.00
    check (limit_max_cost_usd > 0 and limit_max_cost_usd <= 50),
  plan_approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (score_threshold_qualified > score_threshold_needs_review)
);

create index campaigns_user_id_created_at_idx on public.campaigns (user_id, created_at desc);

alter table public.campaigns enable row level security;

create policy "campaigns_select_own" on public.campaigns
  for select
  using (auth.uid () = user_id);

create policy "campaigns_insert_own" on public.campaigns
  for insert
  with check (auth.uid () = user_id);

create policy "campaigns_update_own" on public.campaigns
  for update
  using (auth.uid () = user_id)
  with check (auth.uid () = user_id);

create policy "campaigns_delete_own" on public.campaigns
  for delete
  using (auth.uid () = user_id);

create trigger campaigns_set_updated_at
  before update on public.campaigns
  for each row
  execute function public.set_updated_at ();

create table public.campaign_icp (
  campaign_id uuid primary key references public.campaigns (id) on delete cascade,
  industries text[] not null default '{}',
  locations text[] not null default '{}',
  company_size_min integer,
  company_size_max integer,
  signals text[] not null default '{}',
  exclusions text[] not null default '{}',
  target_roles text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.campaign_icp enable row level security;

create policy "campaign_icp_select_own" on public.campaign_icp
  for select
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_icp.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  );

create policy "campaign_icp_insert_own" on public.campaign_icp
  for insert
  with check (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_icp.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  );

create policy "campaign_icp_update_own" on public.campaign_icp
  for update
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_icp.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  )
  with check (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_icp.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  );

create policy "campaign_icp_delete_own" on public.campaign_icp
  for delete
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_icp.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  );

create trigger campaign_icp_set_updated_at
  before update on public.campaign_icp
  for each row
  execute function public.set_updated_at ();
