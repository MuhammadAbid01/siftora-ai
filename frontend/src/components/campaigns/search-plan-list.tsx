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
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No search plan yet — generate a plan first.
          </p>
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
            <li key={`${item.query}-${index}`} className="flex gap-3 text-sm">
              <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {index + 1}
              </span>
              <div>
                <p className="font-medium text-slate-900 dark:text-slate-100">{item.query}</p>
                <p className="text-slate-500 dark:text-slate-400">{item.rationale}</p>
              </div>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
