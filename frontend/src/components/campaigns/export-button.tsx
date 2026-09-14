"use client";

import { useState } from "react";
import { env } from "@/lib/env";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";

export function ExportButton({ campaignId }: { campaignId: string }) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
      setExporting(false);
      return;
    }

    try {
      const response = await fetch(
        `${env.NEXT_PUBLIC_API_BASE_URL}/api/campaigns/${campaignId}/export`,
        { method: "POST", headers: { Authorization: `Bearer ${accessToken}` } },
      );
      if (!response.ok) {
        throw new Error("Export failed.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `campaign-${campaignId}-export.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not export approved leads.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <Button
        size="sm"
        variant="secondary"
        onClick={() => void handleExport()}
        disabled={exporting}
      >
        {exporting ? "Exporting..." : "Export approved (CSV)"}
      </Button>
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
