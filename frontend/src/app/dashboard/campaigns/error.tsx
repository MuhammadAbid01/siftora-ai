"use client";

import { RouteError } from "@/components/ui/route-error";

export default function CampaignsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteError error={error} reset={reset} message="Something went wrong loading campaigns." />
  );
}
