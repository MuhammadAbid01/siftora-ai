"use client";

import { useCallback, useEffect, useState } from "react";

/** Persists a string value to localStorage, UI-only (no backend sync).
 * Returns the current value, a setter, and whether the client-side read
 * has completed (so callers can avoid a hydration-mismatch flash). */
export function useLocalStorage(key: string, initialValue: string) {
  const [value, setValue] = useState(initialValue);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(key);
      if (stored !== null) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setValue(stored);
      }
    } catch {
      // localStorage unavailable (private mode, etc.) — fall back silently.
    }
    setHydrated(true);
  }, [key]);

  const update = useCallback(
    (next: string) => {
      setValue(next);
      try {
        window.localStorage.setItem(key, next);
      } catch {
        // Ignore — the in-memory value still updates for this session.
      }
    },
    [key],
  );

  return [value, update, hydrated] as const;
}
