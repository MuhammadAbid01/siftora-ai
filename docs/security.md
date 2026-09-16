# Security review (Phase 5)

This document covers `plan.md` §21's security requirements one by one: what's
in place, how it's enforced, how it's tested, and what's explicitly out of
scope for this MVP. See `specs/phase-5-hardening.md` for the phase that
closed most of these gaps.

## RLS plus API ownership checks

Every user-owned table (`campaigns`, `campaign_icp`, `leads`, `lead_evidence`,
`score_breakdowns`, `campaign_runs`, `agent_events`, `tool_calls`,
`outreach_drafts`, `approvals`, `suppression_entries`) has Row Level Security
enabled, scoped to `auth.uid()` (directly, or via a join back to
`campaigns.user_id`). The backend's Supabase client uses the service-role
key, which bypasses RLS — so RLS alone is not the enforcement boundary. Every
repository function in `backend/app/database.py` and every router filters by
the `user_id` extracted from the **verified JWT** (`app/deps.py::
get_current_user`), never a client-supplied id. `companies` is the one
global, non-user-owned table (public business facts, not personal data) and
has no RLS by design.

Cross-user access returns `404`, not `403` — this project doesn't
distinguish "exists but not yours" from "doesn't exist" in its error
responses, so a user can't probe for the existence of another user's
campaign IDs.

## URL validation and SSRF defense

`app/providers.py::is_safe_extraction_url()` rejects non-`http(s)` schemes
and hostnames that are (or are literal IPs in) loopback, link-local,
private, reserved, or multicast ranges — including the cloud metadata
endpoint (`169.254.169.254`), a classic SSRF target. `app/agent.py::
analyze_candidate` calls it before any extraction attempt; a candidate that
fails is persisted as `rejected`/`decision_reason="unsafe_url"`, not
silently dropped or crashed on.

This is a syntactic check on the URL string, not a DNS-resolution-based one
— it does not defend against DNS rebinding (a hostname that resolves to a
public IP at check time but a private one at fetch time). That's a real,
known gap for this MVP; closing it would mean resolving the hostname
ourselves and re-validating the resolved IP immediately before connecting
(and pinning the connection to that IP), which is real additional
complexity with no current AC requiring it. The real extraction adapter
(Firecrawl) does its own server-side fetching, so this check is defense in
depth on our side, not the only line of defense.

## Prompt-injection defenses / scraped content as untrusted input

Every place an LLM prompt interpolates third-party text — a scraped
page's body (`analyze_company`) or an evidence excerpt originally drawn from
one (`draft_outreach`) — wraps it in an explicit `<untrusted_content>` block
instructing the model to treat it as data, never as instructions to follow
(`app/providers.py::_untrusted_block`). This is a standard, cheap first line
of defense, not a guarantee: a sufficiently adversarial page could still
influence a real model's output. It does not need a defense at all in
fixture mode, since the fixture provider never constructs a prompt.

The bigger structural defense is that **the LLM never has the authority to
act** — it only ever returns JSON that's immediately Pydantic-validated
(`CompanyAnalysis`, `DraftOutreachResult`) and then run through
deterministic code (`app/scoring.py`, `app/outreach.py`) that enforces the
actual rules. A successful prompt injection could at worst produce a bad
`CriterionSignals` value or an ungrounded `evidence_refs` — both of which
downstream deterministic checks already catch (bad scores are just bad
scores within a fixed 0–100 range; an ungrounded draft is caught by
`check_quality` and flagged `needs_review`, never silently approved).

## Sanitized rendered content

The frontend never uses `dangerouslySetInnerHTML` anywhere (verified by
`grep -rn dangerouslySetInnerHTML frontend/src` — zero matches). Every piece
of scraped/LLM-derived text (evidence claims/excerpts, draft subject/body)
is rendered through ordinary React child interpolation (`{value}`), which
HTML-escapes by default. There is no code path where untrusted text becomes
markup.

## Allowlisted tools and validated arguments

The research agent (`app/agent.py`) is not a dynamic tool-calling LLM agent
that picks from an open-ended tool set — its graph nodes are fixed Python
functions, and the LLM only ever returns structured, Pydantic-validated
JSON (never a tool name or arbitrary code). "Allowlisting" is therefore
structural: there is no mechanism by which a prompt-injected response could
cause a different function to run or a validated model's constraints to be
bypassed.

## Server-only secrets

`OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `RESEND_API_KEY`,
`SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_JWT_SECRET` are all
backend-only environment variables (`backend/app/config.py`), read once at
startup and never included in any API response schema. The frontend only
ever holds `NEXT_PUBLIC_SUPABASE_ANON_KEY` (public by Supabase's own design
— RLS is what makes it safe) and calls the backend with a user's own bearer
JWT, never a service credential.

**Finding, outside this codebase's control:** this development
environment's local git remote (`.git/config`, not a file in the repo) has
a GitHub personal access token embedded in the HTTPS remote URL, visible in
plaintext to anyone who runs `git remote -v` or reads that config file.
This is a real secret-hygiene issue, but it's the user's local git
configuration, not application code — `CLAUDE.md`'s Git Safety Protocol
explicitly forbids an agent updating git config, so this is flagged here
rather than silently changed. **Status: open.** Recommended remediation:
switch the remote to SSH or a credential helper instead of an embedded-token
HTTPS URL, and rotate the token (it's been visible in terminal output).

## Rate limiting

`app/rate_limit.py` is an in-process, per-user sliding-window limiter
applied to the four routes that either cost real money (LLM/search/
extraction calls) or take an external-facing action:

| Route | Limit |
| --- | --- |
| `POST /campaigns/:id/plan` | 10/min |
| `POST /campaigns/:id/run` | 5/min |
| `POST /leads/:id/regenerate-outreach` | 20/min |
| `POST /approvals/:id/send` | 20/min |

`plan.md` §21 specifically names "auth, planning, and run start." Auth
itself (sign-up/sign-in) never passes through this FastAPI backend — the
frontend calls Supabase Auth directly (see `docs/architecture.md`) — so its
rate limiting is Supabase's own, not something this codebase controls.

The limiter is in-process memory: it resets on restart and does not
coordinate across multiple backend instances. That's an accepted limitation
for this MVP's single-FastAPI-process deployment model (`plan.md` §5/§6) —
a real multi-instance deployment would need a shared store (Redis).

## Admin gating

`app/deps.py::get_current_admin_user` checks `profiles.role == 'admin'`
before allowing `POST /evals/run` (the one endpoint that can spend real
provider budget on demand and exposes internal pass/fail detail —
`plan.md` §7's "Admin — inspect system health, usage, cost, and provider
failures"). There is no self-service admin sign-up. To promote a user,
an operator sets it directly:

```sql
update public.profiles set role = 'admin' where id = '<user-id>';
```

## Suppression, approval, and export guardrails (Phase 4, unchanged)

Not re-litigated here — see `specs/phase-4-outreach.md` for the full design
of suppression checks, the human-approval requirement, and why an
unapproved draft can never be exported or sent. Nothing in Phase 5 changes
any of it.
