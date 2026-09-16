import type { Metadata } from "next";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { profileResponseSchema, type ProfileResponse } from "@/lib/types/api";
import { SettingsView } from "@/components/dashboard/settings-view";
import { Alert } from "@/components/ui/alert";

export const metadata: Metadata = {
  title: "Settings",
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

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const { tab } = await searchParams;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadProfile(session.access_token);

  if ("errorMessage" in result) {
    return <Alert>{result.errorMessage}</Alert>;
  }

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Manage your profile, preferences, and account.
        </p>
      </div>
      <SettingsView profile={result.profile} initialTab={tab} />
    </div>
  );
}
