import type { Metadata } from "next";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { profileResponseSchema } from "@/lib/types/api";
import { EvaluationRunner } from "@/components/dashboard/evaluation-runner";
import { Alert } from "@/components/ui/alert";

export const metadata: Metadata = {
  title: "Evaluation",
};

export default async function EvaluationPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  let isAdmin = false;
  try {
    const profile = await apiGet("/api/me", profileResponseSchema, {
      accessToken: session.access_token,
    });
    isAdmin = profile.role === "admin";
  } catch (error) {
    return (
      <Alert>
        {error instanceof ApiError
          ? `Could not load your profile (${error.code}).`
          : "Could not load your profile."}
      </Alert>
    );
  }

  if (!isAdmin) {
    return (
      <Alert
        variant="warning"
        title="Admin access required"
        icon={
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path
              d="M10 3.5 2.5 16.5h15L10 3.5Zm0 5.5v3.5m0 2.5h.008"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        }
      >
        Running the evaluation harness is limited to admin accounts — see docs/security.md for how
        to promote one.
      </Alert>
    );
  }

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Evaluation
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Runs the deterministic evaluation harness against the currently configured providers.
        </p>
      </div>
      <EvaluationRunner />
    </div>
  );
}
