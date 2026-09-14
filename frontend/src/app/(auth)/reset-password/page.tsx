import type { Metadata } from "next";
import Link from "next/link";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export const metadata: Metadata = {
  title: "Reset password",
};

export default function ResetPasswordPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Reset your password</h1>
      <ResetPasswordForm />
      <p className="mt-6 text-sm text-slate-500">
        <Link href="/sign-in" className="font-medium text-indigo-600 hover:text-indigo-500">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
