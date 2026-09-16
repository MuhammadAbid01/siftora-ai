"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiPost, ApiError } from "@/lib/api-client";
import { demoResetResponseSchema } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function DemoResetButton() {
  const router = useRouter();
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReset = async () => {
    if (
      !window.confirm(
        "This deletes all of your own campaigns, leads, and drafts. This cannot be undone. Continue?",
      )
    ) {
      return;
    }

    setResetting(true);
    setError(null);
    setMessage(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
      setResetting(false);
      return;
    }

    try {
      const result = await apiPost("/api/demo/reset", {}, demoResetResponseSchema, {
        accessToken,
      });
      setMessage(`Deleted ${result.deleted_campaigns} campaign(s).`);
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reset demo data.");
    } finally {
      setResetting(false);
    }
  };

  return (
    <div>
      <Button size="sm" variant="secondary" onClick={() => void handleReset()} disabled={resetting}>
        {resetting ? "Resetting..." : "Reset demo data"}
      </Button>
      {message && (
        <Alert variant="success" className="mt-3">
          {message}
        </Alert>
      )}
      {error && <Alert className="mt-3">{error}</Alert>}
    </div>
  );
}
