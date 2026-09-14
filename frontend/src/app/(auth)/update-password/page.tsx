import type { Metadata } from "next";
import { UpdatePasswordForm } from "@/components/auth/update-password-form";

export const metadata: Metadata = {
  title: "Update password",
};

export default function UpdatePasswordPage() {
  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-slate-900">Set a new password</h1>
      <UpdatePasswordForm />
    </div>
  );
}
