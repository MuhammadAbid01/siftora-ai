import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider, THEME_STORAGE_KEY } from "@/lib/theme/theme-provider";
import "./globals.css";

// Runs before hydration so the correct theme paints on the first frame —
// otherwise a dark-mode visitor would see a light flash. Kept in sync with
// ThemeProvider's own resolution logic (light/dark/system + localStorage).
const THEME_INIT_SCRIPT = `(function(){try{var k=${JSON.stringify(THEME_STORAGE_KEY)};var s=localStorage.getItem(k);var t=(s==="light"||s==="dark"||s==="system")?s:"system";var r=t==="system"?(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):t;document.documentElement.dataset.theme=r;}catch(e){}})();`;

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Siftora — Agentic Lead Intelligence Platform",
    template: "%s | Siftora",
  },
  description:
    "Siftora researches companies, verifies evidence, qualifies prospects, and drafts personalized outreach — always with human approval before any external action.",
  openGraph: {
    title: "Siftora — Agentic Lead Intelligence Platform",
    description:
      "Evidence-backed lead research and qualification, with a mandatory human approval gate before outreach.",
    url: siteUrl,
    siteName: "Siftora",
    type: "website",
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
