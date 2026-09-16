"use client";

import { RouteError } from "@/components/ui/route-error";

export default function LeadsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <RouteError error={error} reset={reset} message="Something went wrong loading leads." />;
}
