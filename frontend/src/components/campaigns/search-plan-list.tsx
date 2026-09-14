import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SearchPlanQueryItem } from "@/lib/types/api";

export function SearchPlanList({ searchPlan }: { searchPlan: SearchPlanQueryItem[] | null }) {
  if (!searchPlan || searchPlan.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Search plan</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">No search plan yet — generate a plan first.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search plan</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-3">
          {searchPlan.map((item, index) => (
            <li key={`${item.query}-${index}`} className="text-sm">
              <p className="font-medium text-slate-900">{item.query}</p>
              <p className="text-slate-500">{item.rationale}</p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
