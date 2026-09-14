-- Phase 3: research runs, companies, leads, evidence, scoring, and agent
-- observability tables. See specs/phase-3-research.md for design rationale.

alter table public.campaigns drop constraint campaigns_status_check;
alter table public.campaigns add constraint campaigns_status_check
  check (status in ('draft', 'awaiting_plan_approval', 'plan_approved', 'queued', 'running', 'completed', 'failed', 'paused'));

-- Global, deduplicated by domain. Not user-owned (public business facts),
-- so no RLS — only the backend's service-role client ever touches it.
create table public.companies (
  id uuid primary key default gen_random_uuid (),
  domain text not null unique,
  name text not null,
  facts jsonb not null default '{}'::jsonb,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger companies_set_updated_at
  before update on public.companies
  for each row
  execute function public.set_updated_at ();

create table public.campaign_runs (
  id uuid primary key default gen_random_uuid (),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'completed', 'failed', 'paused')),
  stop_reason text,
  pause_requested boolean not null default false,
  config_snapshot jsonb not null,
  queries_used integer not null default 0,
  leads_created integer not null default 0,
  qualified_count integer not null default 0,
  needs_review_count integer not null default 0,
  rejected_count integer not null default 0,
  failed_count integer not null default 0,
  estimated_cost_usd numeric(10, 2) not null default 0,
  error text,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index campaign_runs_campaign_id_created_at_idx on public.campaign_runs (campaign_id, created_at desc);

alter table public.campaign_runs enable row level security;

create policy "campaign_runs_select_own" on public.campaign_runs
  for select
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = campaign_runs.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  );

create trigger campaign_runs_set_updated_at
  before update on public.campaign_runs
  for each row
  execute function public.set_updated_at ();

create table public.leads (
  id uuid primary key default gen_random_uuid (),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  company_id uuid not null references public.companies (id) on delete cascade,
  source_url text not null,
  status text not null check (status in ('qualified', 'needs_review', 'rejected')),
  score integer not null check (score between 0 and 100),
  decision_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (campaign_id, company_id)
);

create index leads_campaign_id_idx on public.leads (campaign_id);

alter table public.leads enable row level security;

create policy "leads_select_own" on public.leads
  for select
  using (
    exists (
      select 1 from public.campaigns
      where campaigns.id = leads.campaign_id
        and campaigns.user_id = auth.uid ()
    )
  );

create trigger leads_set_updated_at
  before update on public.leads
  for each row
  execute function public.set_updated_at ();

create table public.lead_evidence (
  id uuid primary key default gen_random_uuid (),
  lead_id uuid not null references public.leads (id) on delete cascade,
  type text not null check (type in ('fact', 'inference', 'unknown')),
  claim text not null,
  excerpt text,
  source_url text,
  confidence numeric(3, 2),
  created_at timestamptz not null default now()
);

create index lead_evidence_lead_id_idx on public.lead_evidence (lead_id);

alter table public.lead_evidence enable row level security;

create policy "lead_evidence_select_own" on public.lead_evidence
  for select
  using (
    exists (
      select 1 from public.leads
      join public.campaigns on campaigns.id = leads.campaign_id
      where leads.id = lead_evidence.lead_id
        and campaigns.user_id = auth.uid ()
    )
  );

create table public.score_breakdowns (
  id uuid primary key default gen_random_uuid (),
  lead_id uuid not null references public.leads (id) on delete cascade,
  criterion text not null check (
    criterion in (
      'industry_fit', 'geography_fit', 'company_size_fit', 'pain_point_evidence',
      'buying_signal', 'contact_relevance', 'recency', 'evidence_completeness'
    )
  ),
  rating numeric(3, 2) not null,
  weight integer not null,
  points numeric(5, 2) not null,
  created_at timestamptz not null default now(),
  unique (lead_id, criterion)
);

create index score_breakdowns_lead_id_idx on public.score_breakdowns (lead_id);

alter table public.score_breakdowns enable row level security;

create policy "score_breakdowns_select_own" on public.score_breakdowns
  for select
  using (
    exists (
      select 1 from public.leads
      join public.campaigns on campaigns.id = leads.campaign_id
      where leads.id = score_breakdowns.lead_id
        and campaigns.user_id = auth.uid ()
    )
  );

create table public.agent_events (
  id uuid primary key default gen_random_uuid (),
  run_id uuid not null references public.campaign_runs (id) on delete cascade,
  node text not null,
  status text not null check (status in ('ok', 'error')),
  summary text not null,
  duration_ms integer,
  error text,
  created_at timestamptz not null default now()
);

create index agent_events_run_id_created_at_idx on public.agent_events (run_id, created_at desc);

alter table public.agent_events enable row level security;

create policy "agent_events_select_own" on public.agent_events
  for select
  using (
    exists (
      select 1 from public.campaign_runs
      join public.campaigns on campaigns.id = campaign_runs.campaign_id
      where campaign_runs.id = agent_events.run_id
        and campaigns.user_id = auth.uid ()
    )
  );

create table public.tool_calls (
  id uuid primary key default gen_random_uuid (),
  run_id uuid not null references public.campaign_runs (id) on delete cascade,
  tool text not null,
  provider text not null,
  status text not null check (status in ('ok', 'error')),
  summary text not null,
  latency_ms integer,
  cost_usd numeric(10, 4),
  created_at timestamptz not null default now()
);

create index tool_calls_run_id_created_at_idx on public.tool_calls (run_id, created_at desc);

alter table public.tool_calls enable row level security;

create policy "tool_calls_select_own" on public.tool_calls
  for select
  using (
    exists (
      select 1 from public.campaign_runs
      join public.campaigns on campaigns.id = campaign_runs.campaign_id
      where campaign_runs.id = tool_calls.run_id
        and campaigns.user_id = auth.uid ()
    )
  );
