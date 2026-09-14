import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProfileResponse } from "@/lib/types/api";

export function ProfileCard({ profile }: { profile: ProfileResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your profile</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
          <dt className="font-medium text-slate-500">Email</dt>
          <dd className="text-slate-900">{profile.email}</dd>
          <dt className="font-medium text-slate-500">Role</dt>
          <dd className="text-slate-900">{profile.role}</dd>
          <dt className="font-medium text-slate-500">Member since</dt>
          <dd className="text-slate-900">{new Date(profile.created_at).toLocaleDateString()}</dd>
        </dl>
      </CardContent>
    </Card>
  );
}
