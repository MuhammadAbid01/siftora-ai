"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useLocalStorage } from "@/lib/use-local-storage";

const SIDEBAR_STORAGE_KEY = "siftora-sidebar-collapsed";

type SidebarContextValue = {
  collapsed: boolean;
  toggle: () => void;
};

const SidebarContext = createContext<SidebarContextValue>({
  collapsed: false,
  toggle: () => {},
});

/** Desktop sidebar collapse/expand state, persisted to localStorage. Shared
 * between `DashboardNav` (which renders the collapse toggle and adapts its
 * own width) and `DashboardShell` (which adapts the content area's left
 * padding to match) — the two have no parent/child relationship. */
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = useLocalStorage(SIDEBAR_STORAGE_KEY, "expanded");
  const collapsed = stored === "collapsed";

  const value = useMemo(
    () => ({
      collapsed,
      toggle: () => setStored(collapsed ? "expanded" : "collapsed"),
    }),
    [collapsed, setStored],
  );

  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>;
}

export function useSidebar() {
  return useContext(SidebarContext);
}
