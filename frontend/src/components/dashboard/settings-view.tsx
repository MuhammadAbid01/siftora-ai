"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useLocalStorage } from "@/lib/use-local-storage";
import { useDensity } from "@/lib/density/density-provider";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { DemoResetButton } from "@/components/dashboard/demo-reset-button";
import { cn } from "@/lib/cn";
import type { ProfileResponse } from "@/lib/types/api";

const TABS = ["Profile", "Preferences", "Account"] as const;
type Tab = (typeof TABS)[number];

const TAB_SLUGS: Record<Tab, string> = {
  Profile: "profile",
  Preferences: "preferences",
  Account: "account",
};

function tabFromSlug(slug: string | undefined): Tab {
  const match = TABS.find((tab) => TAB_SLUGS[tab] === slug);
  return match ?? "Profile";
}

const DISPLAY_NAME_KEY = "siftora-display-name";

function LocalOnlyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
      <svg
        width="12"
        height="12"
        viewBox="0 0 16 16"
        fill="none"
        aria-hidden="true"
        className="shrink-0"
      >
        <path
          d="M8 5.5v3m0 3h.007M14.5 8A6.5 6.5 0 1 1 1.5 8a6.5 6.5 0 0 1 13 0Z"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {children}
    </p>
  );
}

function ProfileTab({ profile }: { profile: ProfileResponse }) {
  const [displayName, setDisplayName] = useLocalStorage(DISPLAY_NAME_KEY, "");
  const [draft, setDraft] = useState(displayName);
  const [saved, setSaved] = useState(false);
  const initial = (displayName || profile.email).charAt(0).toUpperCase();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Avatar</CardTitle>
          <CardDescription>
            Shown as your initials — there&apos;s no photo upload yet, so this always reflects your
            display name or email.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <span className="flex size-16 items-center justify-center rounded-full bg-indigo-600 text-xl font-semibold text-white dark:bg-indigo-500">
            {initial}
          </span>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Display name</CardTitle>
          <CardDescription>Used only in this app&apos;s interface.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Label htmlFor="display-name" className="sr-only">
            Display name
          </Label>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Input
              id="display-name"
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
                setSaved(false);
              }}
              placeholder={profile.email.split("@")[0]}
              className="sm:max-w-xs"
            />
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setDisplayName(draft.trim());
                setSaved(true);
              }}
            >
              {saved ? "Saved" : "Save"}
            </Button>
          </div>
          <LocalOnlyNote>
            Saved on this device only (browser storage) — not yet stored on your account.
          </LocalOnlyNote>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Email</CardTitle>
          <CardDescription>From your account — not editable here yet.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-900 dark:text-slate-100">{profile.email}</p>
        </CardContent>
      </Card>
    </div>
  );
}

function PreferencesTab() {
  const { density, setDensity } = useDensity();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Theme</CardTitle>
          <CardDescription>Applies immediately and is remembered on this device.</CardDescription>
        </CardHeader>
        <CardContent>
          <ThemeToggle />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Density</CardTitle>
          <CardDescription>Compact mode trims padding on cards and panels.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div
            role="radiogroup"
            aria-label="Density"
            className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 dark:border-slate-800 dark:bg-slate-900"
          >
            {(["comfortable", "compact"] as const).map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={density === option}
                onClick={() => setDensity(option)}
                className={cn(
                  "rounded-md px-3.5 py-1.5 text-sm font-medium capitalize transition-colors duration-150",
                  density === option
                    ? "bg-white text-indigo-600 shadow-xs dark:bg-slate-700 dark:text-indigo-300"
                    : "text-slate-500 hover:text-slate-900 dark:text-slate-500 dark:hover:text-slate-200",
                )}
              >
                {option}
              </button>
            ))}
          </div>
          <LocalOnlyNote>Saved on this device only.</LocalOnlyNote>
        </CardContent>
      </Card>
    </div>
  );
}

function AccountTab({ profile }: { profile: ProfileResponse }) {
  const router = useRouter();

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Account details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
            <dt className="font-medium text-slate-500 dark:text-slate-400">Role</dt>
            <dd>
              <Badge variant={profile.role === "admin" ? "brand" : "neutral"}>{profile.role}</Badge>
            </dd>
            <dt className="font-medium text-slate-500 dark:text-slate-400">Member since</dt>
            <dd className="text-slate-900 dark:text-slate-100">
              {new Date(profile.created_at).toLocaleDateString()}
            </dd>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
        </CardHeader>
        <CardContent>
          <Button variant="secondary" size="sm" onClick={() => void handleSignOut()}>
            Sign out
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Demo data</CardTitle>
          <CardDescription>
            Delete every campaign this account owns to reset to a clean slate.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DemoResetButton />
        </CardContent>
      </Card>
    </div>
  );
}

export function SettingsView({
  profile,
  initialTab,
}: {
  profile: ProfileResponse;
  initialTab?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [tab, setTab] = useState<Tab>(() => tabFromSlug(initialTab));

  const selectTab = (next: Tab) => {
    setTab(next);
    router.replace(`${pathname}?tab=${TAB_SLUGS[next]}`, { scroll: false });
  };

  return (
    <div>
      <div
        role="tablist"
        aria-label="Settings sections"
        className="mb-6 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 dark:border-slate-800 dark:bg-slate-900"
      >
        {TABS.map((label) => (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={tab === label}
            onClick={() => selectTab(label)}
            className={cn(
              "rounded-md px-4 py-1.5 text-sm font-medium transition-colors duration-150",
              tab === label
                ? "bg-white text-indigo-600 shadow-xs dark:bg-slate-700 dark:text-indigo-300"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="motion-safe:animate-fade-in">
        {tab === "Profile" && <ProfileTab profile={profile} />}
        {tab === "Preferences" && <PreferencesTab />}
        {tab === "Account" && <AccountTab profile={profile} />}
      </div>
    </div>
  );
}
