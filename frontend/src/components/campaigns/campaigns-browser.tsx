"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CampaignList } from "@/components/campaigns/campaign-list";
import { StatusBadge } from "@/components/campaigns/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { campaignStatusSchema, type CampaignResponse, type CampaignStatus } from "@/lib/types/api";

const STATUS_OPTIONS = campaignStatusSchema.options;
const SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
] as const;
type SortOption = (typeof SORT_OPTIONS)[number]["value"];

/** Client-side search/filter/sort over the campaign list this page already
 * fetched via `GET /api/campaigns` — no additional API calls. */
export function CampaignsBrowser({ campaigns }: { campaigns: CampaignResponse[] }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<CampaignStatus | "all">("all");
  const [sort, setSort] = useState<SortOption>("newest");

  const filtered = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    return campaigns
      .filter((c) => (status === "all" ? true : c.status === status))
      .filter((c) => (trimmed ? c.brief.toLowerCase().includes(trimmed) : true))
      .sort((a, b) => {
        const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        return sort === "newest" ? -diff : diff;
      });
  }, [campaigns, query, status, sort]);

  if (campaigns.length === 0) {
    return (
      <EmptyState
        icon={
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path
              d="M3 6.5A1.5 1.5 0 0 1 4.5 5h11A1.5 1.5 0 0 1 17 6.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 13.5v-7Z"
              stroke="currentColor"
              strokeWidth="1.4"
            />
          </svg>
        }
        title="No campaigns yet"
        description="Create your first campaign to turn a brief into a research plan."
        action={
          <Link
            href="/dashboard/campaigns/new"
            className={cn(buttonVariants({ size: "sm", variant: "secondary" }))}
          >
            Create your first one
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <svg
            width="16"
            height="16"
            viewBox="0 0 20 20"
            fill="none"
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-400"
          >
            <path
              d="m17.5 17.5-3.5-3.5m1.667-4.167a5.833 5.833 0 1 1-11.667 0 5.833 5.833 0 0 1 11.667 0Z"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
            />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by brief..."
            aria-label="Search campaigns"
            className="h-10 w-full rounded-lg border border-slate-200 bg-white pr-3 pl-9 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:border-indigo-500 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500"
          />
        </div>
        <label className="sr-only" htmlFor="campaign-status-filter">
          Filter by status
        </label>
        <select
          id="campaign-status-filter"
          value={status}
          onChange={(event) => setStatus(event.target.value as CampaignStatus | "all")}
          className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus-visible:border-indigo-500 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        >
          <option value="all">All statuses</option>
          {STATUS_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="campaign-sort">
          Sort by
        </label>
        <select
          id="campaign-sort"
          value={sort}
          onChange={(event) => setSort(event.target.value as SortOption)}
          className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus-visible:border-indigo-500 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {status !== "all" && (
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          Filtering by <StatusBadge status={status} />
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          title="No matching campaigns"
          description="Try a different search term or status filter."
        />
      ) : (
        <CampaignList campaigns={filtered} />
      )}
    </div>
  );
}
