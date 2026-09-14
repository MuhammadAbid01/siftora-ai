import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | Siftora",
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-semibold text-slate-900">Terms of Service</h1>
      <p className="mt-4 text-slate-600">
        Siftora is a portfolio project currently in active development. This placeholder page will
        be replaced with complete terms of service before any production deployment.
      </p>
    </div>
  );
}
