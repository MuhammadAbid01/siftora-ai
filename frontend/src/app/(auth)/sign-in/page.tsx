import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { SignInForm } from "@/components/auth/sign-in-form";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function SignInPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Sign in</h1>
      <Suspense fallback={null}>
        <SignInForm />
      </Suspense>
      <div className="mt-6 flex flex-col gap-2 text-sm text-slate-500">
        <Link href="/reset-password" className="font-medium text-indigo-600 hover:text-indigo-500">
          Forgot your password?
        </Link>
        <p>
          Don&apos;t have an account?{" "}
          <Link href="/sign-up" className="font-medium text-indigo-600 hover:text-indigo-500">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
