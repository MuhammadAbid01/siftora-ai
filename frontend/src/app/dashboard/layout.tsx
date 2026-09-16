import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { MobileNavProvider } from "@/components/dashboard/mobile-nav-context";
import { SidebarProvider } from "@/components/dashboard/sidebar-context";
import { DensityProvider } from "@/lib/density/density-provider";

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/sign-in?next=/dashboard");
  }

  return (
    <DensityProvider>
      <SidebarProvider>
        <MobileNavProvider>
          <DashboardShell email={user.email ?? ""}>{children}</DashboardShell>
        </MobileNavProvider>
      </SidebarProvider>
    </DensityProvider>
  );
}
