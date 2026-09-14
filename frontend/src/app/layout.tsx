import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

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
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-white text-slate-900">{children}</body>
    </html>
  );
}
