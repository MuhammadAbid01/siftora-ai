"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

export function DashboardNav({ email }: { email: string }) {
  const router = useRouter();

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  };

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="text-lg font-semibold text-slate-900">
            Siftora
          </Link>
          <nav aria-label="Dashboard" className="flex items-center gap-4">
            <Link
              href="/dashboard/campaigns"
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              Campaigns
            </Link>
            <Link
              href="/dashboard/approvals"
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              Approvals
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-500">{email}</span>
          <Button variant="secondary" size="sm" onClick={handleSignOut}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
