"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useMobileNav } from "@/components/dashboard/mobile-nav-context";
import { useSidebar } from "@/components/dashboard/sidebar-context";
import { cn } from "@/lib/cn";

const NAV_ITEMS = [
  {
    href: "/dashboard",
    label: "Dashboard",
    exact: true,
    icon: (
      <path
        d="M3 8.5 10 3l7 5.5V16a1 1 0 0 1-1 1h-3.5v-5h-5v5H4a1 1 0 0 1-1-1V8.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    ),
  },
  {
    href: "/dashboard/campaigns",
    label: "Campaigns",
    icon: (
      <path
        d="M3 6.5A1.5 1.5 0 0 1 4.5 5h11A1.5 1.5 0 0 1 17 6.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 13.5v-7Z M3 8h14"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    href: "/dashboard/approvals",
    label: "Approvals",
    icon: (
      <path
        d="M4 9.5 8 13l8-8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    href: "/dashboard/evaluation",
    label: "Evaluation",
    icon: (
      <path
        d="M3 15V9m5 6V5m5 10v-4m5 4V8"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    ),
  },
];

const SECONDARY_NAV_ITEMS = [
  {
    href: "/dashboard/settings",
    label: "Settings",
    icon: (
      <>
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
      </>
    ),
  },
];

function NavLinks({
  pathname,
  onNavigate,
  items,
  collapsed,
}: {
  pathname: string;
  onNavigate?: () => void;
  items: typeof NAV_ITEMS;
  collapsed?: boolean;
}) {
  return (
    <>
      {items.map((item) => {
        const active =
          "exact" in item && item.exact ? pathname === item.href : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            title={collapsed ? item.label : undefined}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              collapsed && "justify-center px-2",
              active
                ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100",
            )}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 20 20"
              fill="none"
              aria-hidden="true"
              className={cn(
                "shrink-0",
                active ? "text-indigo-600 dark:text-indigo-300" : "text-slate-400 dark:text-slate-500",
              )}
            >
              {item.icon}
            </svg>
            <span className={collapsed ? "sr-only" : undefined}>{item.label}</span>
          </Link>
        );
      })}
    </>
  );
}

function SidebarContent({
  pathname,
  onNavigate,
  collapsed,
  onToggleCollapse,
}: {
  pathname: string;
  onNavigate?: () => void;
  collapsed?: boolean;
  /** Only passed for the desktop sidebar — the mobile drawer has its own
   * close button and no collapse affordance. */
  onToggleCollapse?: () => void;
}) {
  return (
    <>
      <div
        className={cn(
          "flex h-16 shrink-0 items-center border-b border-slate-200 dark:border-slate-800",
          collapsed ? "justify-center px-2" : "justify-between px-5",
        )}
      >
        <Link
          href="/dashboard"
          onClick={onNavigate}
          className="flex items-center gap-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100"
        >
          <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white dark:bg-indigo-500">
            S
          </span>
          {!collapsed && "Siftora"}
        </Link>
        {onToggleCollapse && !collapsed && (
          <button
            type="button"
            aria-label="Collapse sidebar"
            onClick={onToggleCollapse}
            className="inline-flex size-7 items-center justify-center rounded-md text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <svg width="15" height="15" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M13 4.5 6.5 10l6.5 5.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M4.5 4v12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        )}
      </div>
      <nav aria-label="Dashboard" className="flex-1 space-y-1 overflow-y-auto p-3">
        <NavLinks pathname={pathname} onNavigate={onNavigate} items={NAV_ITEMS} collapsed={collapsed} />
      </nav>
      <div className="space-y-1 border-t border-slate-200 p-3 dark:border-slate-800">
        {onToggleCollapse && collapsed && (
          <button
            type="button"
            aria-label="Expand sidebar"
            onClick={onToggleCollapse}
            className="flex w-full items-center justify-center rounded-lg px-2 py-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <svg width="15" height="15" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M7 4.5 13.5 10 7 15.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M15.5 4v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span className="sr-only">Expand sidebar</span>
          </button>
        )}
        <NavLinks
          pathname={pathname}
          onNavigate={onNavigate}
          items={SECONDARY_NAV_ITEMS}
          collapsed={collapsed}
        />
      </div>
    </>
  );
}

export function DashboardNav() {
  const pathname = usePathname();
  const { open, setOpen } = useMobileNav();
  const { collapsed, toggle } = useSidebar();

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-slate-200 bg-white transition-[width] duration-200 ease-out motion-reduce:transition-none md:flex dark:border-slate-800 dark:bg-slate-950",
          collapsed ? "w-[72px]" : "w-64",
        )}
      >
        <SidebarContent pathname={pathname} collapsed={collapsed} onToggleCollapse={toggle} />
      </aside>

      {/* Mobile drawer — triggered from the hamburger button in Topbar via
          MobileNavProvider (no direct parent/child relationship between them). */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-slate-950/40 motion-safe:animate-fade-in"
            onClick={() => setOpen(false)}
          />
          <div
            id="dashboard-mobile-menu"
            className="relative flex h-full w-72 max-w-[85vw] flex-col border-r border-slate-200 bg-white shadow-xl motion-safe:animate-drawer-in dark:border-slate-800 dark:bg-slate-950"
          >
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setOpen(false)}
              className="absolute top-4 right-3 inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            >
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
            <SidebarContent pathname={pathname} onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
