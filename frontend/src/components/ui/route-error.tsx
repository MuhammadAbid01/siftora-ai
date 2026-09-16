"use client";

import { useEffect } from "react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/** Shared body for every route segment's `error.tsx` boundary — each
 * boundary file still has to exist per Next.js's routing convention, but
 * the actual markup/styling lives here once.
 */
export function RouteError({
  error,
  reset,
  message,
}: {
  error: Error & { digest?: string };
  reset: () => void;
  message: string;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Alert>
      <p className="mb-4">{message}</p>
      <Button variant="secondary" size="sm" onClick={reset}>
        Try again
      </Button>
    </Alert>
  );
}
