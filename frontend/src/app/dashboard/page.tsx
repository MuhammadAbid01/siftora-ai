import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { profileResponseSchema, type ProfileResponse } from "@/lib/types/api";
import { ProfileCard } from "@/components/dashboard/profile-card";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export const metadata: Metadata = {
  title: "Dashboard",
};

async function loadProfile(
  accessToken: string,
): Promise<{ profile: ProfileResponse } | { errorMessage: string }> {
  try {
    const profile = await apiGet("/api/me", profileResponseSchema, { accessToken });
    return { profile };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? `Could not load your profile (${error.code}).`
        : "Could not load your profile. Please try again.";
    return { errorMessage };
  }
}

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        Your session could not be verified. Please sign in again.
      </div>
    );
  }

  const result = await loadProfile(session.access_token);

  if ("errorMessage" in result) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        {result.errorMessage}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Research and outreach automation arrive in later phases — for now, create and plan
          campaigns.
        </p>
      </div>
      <ProfileCard profile={result.profile} />
      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-6">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Campaigns</h2>
          <p className="mt-1 text-sm text-slate-500">
            Turn a brief into an ICP and search plan, then approve it.
          </p>
        </div>
        <Link href="/dashboard/campaigns" className={cn(buttonVariants({ size: "sm" }))}>
          View campaigns
        </Link>
      </div>
    </div>
  );
}
