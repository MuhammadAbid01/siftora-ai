import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import {
  campaignListResponseSchema,
  approvalListResponseSchema,
  type CampaignResponse,
} from "@/lib/types/api";
import { CampaignList } from "@/components/campaigns/campaign-list";
import { EmptyState } from "@/components/ui/empty-state";
import { Alert } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export const metadata: Metadata = {
  title: "Dashboard",
};

const ACTIVE_STATUSES = new Set(["queued", "running"]);

type DashboardData = {
  campaigns: CampaignResponse[];
  pendingApprovals: number;
};

async function loadDashboardData(
  accessToken: string,
): Promise<DashboardData | { errorMessage: string }> {
  try {
    const [campaignsResult, approvalsResult] = await Promise.all([
      apiGet("/api/campaigns", campaignListResponseSchema, { accessToken }),
      apiGet("/api/approvals?status=pending&limit=1", approvalListResponseSchema, {
        accessToken,
      }),
    ]);
    return { campaigns: campaignsResult.items, pendingApprovals: approvalsResult.items.length };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? `Could not load your dashboard (${error.code}).`
        : "Could not load your dashboard. Please try again.";
    return { errorMessage };
  }
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-6">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
          {icon}
        </div>
        <div>
          <p className="text-2xl font-semibold tracking-tight text-slate-900 tabular-nums dark:text-slate-100">
            {value}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadDashboardData(session.access_token);

  if ("errorMessage" in result) {
    return <Alert>{result.errorMessage}</Alert>;
  }

  const { campaigns, pendingApprovals } = result;
  const activeCount = campaigns.filter((c) => ACTIVE_STATUSES.has(c.status)).length;
  const recentCampaigns = [...campaigns]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-8 motion-safe:animate-fade-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Signed in as {session.user.email}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/campaigns/new" className={cn(buttonVariants({ size: "sm" }))}>
            New campaign
          </Link>
          <Link
            href="/dashboard/approvals"
            className={cn(buttonVariants({ size: "sm", variant: "secondary" }))}
          >
            View approvals
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Total campaigns"
          value={campaigns.length}
          icon={
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M3 6.5A1.5 1.5 0 0 1 4.5 5h11A1.5 1.5 0 0 1 17 6.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 13.5v-7Z M3 8h14"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          }
        />
        <StatCard
          label="Active campaigns"
          value={activeCount}
          icon={
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M10 5v5l3.5 2"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
              <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.4" />
            </svg>
          }
        />
        <StatCard
          label="Drafts pending approval"
          value={pendingApprovals}
          icon={
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M4 9.5 8 13l8-8"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          }
        />
      </div>

      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Recent campaigns
          </h2>
          {campaigns.length > 0 && (
            <Link
              href="/dashboard/campaigns"
              className="text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
            >
              View all
            </Link>
          )}
        </div>
        {campaigns.length === 0 ? (
          <EmptyState
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
        ) : (
          <CampaignList campaigns={recentCampaigns} />
        )}
      </div>
    </div>
  );
}
