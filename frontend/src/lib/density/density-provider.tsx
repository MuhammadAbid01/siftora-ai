"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useLocalStorage } from "@/lib/use-local-storage";

export type Density = "comfortable" | "compact";

const DENSITY_STORAGE_KEY = "siftora-density";

const DensityContext = createContext<{
  density: Density;
  setDensity: (density: Density) => void;
}>({
  density: "comfortable",
  setDensity: () => {},
});

/** UI-only compact-mode toggle (Settings > Preferences), persisted to
 * localStorage. Scoped to the dashboard shell — `Card`/`CardHeader`/
 * `CardContent` read this via `useDensity()` to trim padding; components
 * outside a provider (e.g. the public landing page) get the "comfortable"
 * default with no provider required. */
export function DensityProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = useLocalStorage(DENSITY_STORAGE_KEY, "comfortable");
  const density: Density = stored === "compact" ? "compact" : "comfortable";

  const value = useMemo(
    () => ({ density, setDensity: (next: Density) => setStored(next) }),
    [density, setStored],
  );

  return <DensityContext.Provider value={value}>{children}</DensityContext.Provider>;
}

export function useDensity() {
  return useContext(DensityContext);
}
