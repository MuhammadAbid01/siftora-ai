"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useMobileNav } from "@/components/dashboard/mobile-nav-context";
import { getAccessToken } from "@/lib/supabase/access-token";
import { apiGet } from "@/lib/api-client";
import { campaignListResponseSchema, type CampaignResponse } from "@/lib/types/api";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/cn";

const PAGE_TITLES: { match: (path: string) => boolean; title: string }[] = [
  { match: (p) => p === "/dashboard", title: "Dashboard" },
  { match: (p) => p === "/dashboard/campaigns/new", title: "New campaign" },
  { match: (p) => /^\/dashboard\/campaigns\/[^/]+\/leads\/[^/]+/.test(p), title: "Lead" },
  { match: (p) => /^\/dashboard\/campaigns\/[^/]+\/leads/.test(p), title: "Leads" },
  { match: (p) => /^\/dashboard\/campaigns\/[^/]+\/analytics/.test(p), title: "Analytics" },
  { match: (p) => /^\/dashboard\/campaigns\/[^/]+/.test(p), title: "Campaign" },
  { match: (p) => p === "/dashboard/campaigns", title: "Campaigns" },
  { match: (p) => p === "/dashboard/approvals", title: "Approvals" },
  { match: (p) => p === "/dashboard/evaluation", title: "Evaluation" },
  { match: (p) => p === "/dashboard/settings", title: "Settings" },
];

function pageTitleFor(pathname: string): string {
  return PAGE_TITLES.find((entry) => entry.match(pathname))?.title ?? "Dashboard";
}

/** Debounced client-side search over campaigns (reuses `GET /api/campaigns`,
 * the same endpoint the campaigns list page already calls — only fetched
 * lazily when the user types, not on every dashboard page load). */
function useCampaignSearch(query: string) {
  const [results, setResults] = useState<CampaignResponse[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const accessToken = await getAccessToken();
        if (!accessToken) return;
        const response = await apiGet("/api/campaigns", campaignListResponseSchema, {
          accessToken,
        });
        if (cancelled) return;
        const matches = response.items
          .filter((c) => c.brief.toLowerCase().includes(trimmed.toLowerCase()))
          .slice(0, 6);
        setResults(matches);
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  return { results, loading };
}

export function Topbar({ email }: { email: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const title = pageTitleFor(pathname);
  const { setOpen: setMobileNavOpen } = useMobileNav();

  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const { results, loading } = useCampaignSearch(query);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const initial = useMemo(() => email.charAt(0).toUpperCase() || "?", [email]);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/80 px-4 backdrop-blur-md sm:px-6 dark:border-slate-800 dark:bg-slate-950/80">
      <button
        type="button"
        aria-label="Open menu"
        onClick={() => setMobileNavOpen(true)}
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 md:hidden dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      >
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M3 5h14M3 10h14M3 15h14"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>

      <h1 className="hidden shrink-0 text-sm font-semibold text-slate-900 sm:block dark:text-slate-100">
        {title}
      </h1>

      <div ref={searchRef} className="relative ml-0 flex-1 sm:ml-4 sm:max-w-sm">
        <svg
          width="16"
          height="16"
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-400"
        >
          <path
            d="m17.5 17.5-3.5-3.5m1.667-4.167a5.833 5.833 0 1 1-11.667 0 5.833 5.833 0 0 1 11.667 0Z"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setSearchOpen(true);
          }}
          onFocus={() => setSearchOpen(true)}
          placeholder="Search campaigns..."
          aria-label="Search campaigns"
          className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pr-3 pl-9 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:border-indigo-400 focus-visible:bg-white focus-visible:ring-2 focus-visible:ring-indigo-500/30 focus-visible:outline-none dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus-visible:bg-slate-900"
        />
        {searchOpen && query.trim().length >= 2 && (
          <div className="absolute z-40 mt-2 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg motion-safe:animate-scale-in dark:border-slate-800 dark:bg-slate-900">
            {loading && (
              <p className="px-3.5 py-3 text-sm text-slate-500 dark:text-slate-400">Searching…</p>
            )}
            {!loading && results.length === 0 && (
              <p className="px-3.5 py-3 text-sm text-slate-500 dark:text-slate-400">
                No campaigns match &ldquo;{query}&rdquo;.
              </p>
            )}
            {!loading &&
              results.map((campaign) => (
                <button
                  key={campaign.id}
                  type="button"
                  onClick={() => {
                    setSearchOpen(false);
                    setQuery("");
                    router.push(`/dashboard/campaigns/${campaign.id}`);
                  }}
                  className="block w-full truncate px-3.5 py-2.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {campaign.brief}
                </button>
              ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1.5 sm:gap-2.5">
        {/* Notification bell — UI-only, no backend event stream exists yet;
            opens an honest empty state rather than doing nothing on click. */}
        <DropdownMenu
          align="end"
          className="w-72 p-0"
          trigger={() => (
            <span className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100">
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path
                  d="M6 8a4 4 0 1 1 8 0c0 3.5 1.5 4.5 1.5 4.5h-11S6 11.5 6 8Z"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinejoin="round"
                />
                <path
                  d="M8.5 15a1.5 1.5 0 0 0 3 0"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
              </svg>
              <span className="sr-only">Notifications</span>
            </span>
          )}
        >
          <div className="flex flex-col items-center gap-2 px-5 py-8 text-center">
            <div className="flex size-10 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path
                  d="M6 8a4 4 0 1 1 8 0c0 3.5 1.5 4.5 1.5 4.5h-11S6 11.5 6 8Z"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinejoin="round"
                />
                <path
                  d="M8.5 15a1.5 1.5 0 0 0 3 0"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
              No notifications yet
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              There&apos;s no notification system wired up yet — this is a placeholder for where
              campaign and approval alerts will show up.
            </p>
          </div>
        </DropdownMenu>

        <ThemeToggle className="hidden sm:inline-flex" />

        <DropdownMenu
          align="end"
          trigger={() => (
            <span className="flex size-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white transition-transform duration-150 motion-safe:hover:scale-105 dark:bg-indigo-500">
              {initial}
            </span>
          )}
        >
          <DropdownMenuLabel>{email}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => router.push("/dashboard/settings?tab=profile")}>
            <IconUser /> Profile
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => router.push("/dashboard/settings?tab=preferences")}>
            <IconSettings /> Settings
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem destructive onSelect={() => void handleSignOut()}>
            <IconSignOut /> Sign out
          </DropdownMenuItem>
        </DropdownMenu>
      </div>
    </header>
  );
}

function IconUser() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      className={cn("shrink-0")}
    >
      <path
        d="M10 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-6 7c0-3 2.5-5.5 6-5.5s6 2.5 6 5.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <path
        d="M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path
        d="M16.17 12.5a1.4 1.4 0 0 0 .28 1.53l.05.05a1.7 1.7 0 1 1-2.4 2.4l-.05-.05a1.4 1.4 0 0 0-1.53-.28 1.4 1.4 0 0 0-.85 1.28V17.5a1.7 1.7 0 0 1-3.4 0v-.08a1.4 1.4 0 0 0-.92-1.28 1.4 1.4 0 0 0-1.53.28l-.05.05a1.7 1.7 0 1 1-2.4-2.4l.05-.05a1.4 1.4 0 0 0 .28-1.53 1.4 1.4 0 0 0-1.28-.85H2.5a1.7 1.7 0 0 1 0-3.4h.08a1.4 1.4 0 0 0 1.28-.92 1.4 1.4 0 0 0-.28-1.53l-.05-.05a1.7 1.7 0 1 1 2.4-2.4l.05.05a1.4 1.4 0 0 0 1.53.28h.06a1.4 1.4 0 0 0 .85-1.28V2.5a1.7 1.7 0 0 1 3.4 0v.08a1.4 1.4 0 0 0 .85 1.28h.06a1.4 1.4 0 0 0 1.53-.28l.05-.05a1.7 1.7 0 1 1 2.4 2.4l-.05.05a1.4 1.4 0 0 0-.28 1.53v.06a1.4 1.4 0 0 0 1.28.85h.08a1.7 1.7 0 0 1 0 3.4h-.08a1.4 1.4 0 0 0-1.28.85Z"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconSignOut() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <path
        d="M7.5 17.5h-3a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1h3M13.5 14l4-4-4-4M17.5 10h-10"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
