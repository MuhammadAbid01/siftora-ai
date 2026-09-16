"use client";

import { useState } from "react";
import { apiPost, ApiError } from "@/lib/api-client";
import { evalReportSchema, type EvalReport } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function EvaluationRunner() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
      setRunning(false);
      return;
    }

    try {
      const result = await apiPost("/api/evals/run", {}, evalReportSchema, { accessToken });
      setReport(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run the evaluation harness.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <Button onClick={() => void handleRun()} disabled={running}>
          {running ? "Running..." : "Run evaluations"}
        </Button>
        {error && <Alert className="mt-2">{error}</Alert>}
      </div>

      {report && (
        <div className="space-y-4 motion-safe:animate-fade-in-up">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <CardTitle>
                  Overall:{" "}
                  <span className="tabular-nums">
                    {(report.overall_pass_rate * 100).toFixed(0)}%
                  </span>{" "}
                  pass rate
                </CardTitle>
                <Badge variant={report.overall_pass_rate === 1 ? "success" : "warning"}>
                  {report.overall_pass_rate === 1 ? "All passing" : "Needs attention"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Providers exercised: llm={report.provider_mode.llm}, search=
                {report.provider_mode.search}, extraction={report.provider_mode.extraction}
              </p>
            </CardContent>
          </Card>

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-[var(--shadow-card)] dark:border-slate-800 dark:bg-slate-900 dark:shadow-[var(--shadow-card-dark)]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                <tr>
                  <th className="px-4 py-2.5 font-medium text-slate-600 dark:text-slate-400">
                    Category
                  </th>
                  <th className="px-4 py-2.5 font-medium text-slate-600 dark:text-slate-400">
                    Passed
                  </th>
                  <th className="px-4 py-2.5 font-medium text-slate-600 dark:text-slate-400">
                    Pass rate
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {report.categories.map((category) => (
                  <tr
                    key={category.category}
                    className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/60"
                  >
                    <td className="px-4 py-2.5 font-medium text-slate-900 dark:text-slate-100">
                      {formatCategory(category.category)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-700 tabular-nums dark:text-slate-300">
                      {category.passed}/{category.total}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant={category.pass_rate === 1 ? "success" : "warning"}>
                        {(category.pass_rate * 100).toFixed(0)}%
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
