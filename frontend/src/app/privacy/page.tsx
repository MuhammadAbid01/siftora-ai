import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy | Siftora",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 motion-safe:animate-fade-in">
      <Link
        href="/"
        className="mb-8 inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
      >
        <span className="flex size-6 items-center justify-center rounded-md bg-indigo-600 text-xs font-bold text-white dark:bg-indigo-500">
          S
        </span>
        Back to Siftora
      </Link>
      <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        Privacy Policy
      </h1>
      <p className="mt-4 text-slate-600 dark:text-slate-400">
        Siftora is a portfolio project currently in active development. This placeholder page will
        be replaced with a complete privacy policy before any production deployment collects real
        user data.
      </p>
    </div>
  );
}
