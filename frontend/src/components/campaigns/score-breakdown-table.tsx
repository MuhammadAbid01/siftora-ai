import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ScoreBreakdownItem } from "@/lib/types/api";

const CRITERION_LABELS: Record<string, string> = {
  industry_fit: "Industry fit",
  geography_fit: "Geography fit",
  company_size_fit: "Company-size fit",
  pain_point_evidence: "Pain-point evidence",
  buying_signal: "Buying/tech signal",
  contact_relevance: "Contact relevance",
  recency: "Website/activity recency",
  evidence_completeness: "Evidence completeness",
};

export function ScoreBreakdownTable({ breakdown }: { breakdown: ScoreBreakdownItem[] }) {
  if (breakdown.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Score breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">This lead was never scored.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="pb-2 font-medium">Criterion</th>
                <th className="pb-2 font-medium">Rating</th>
                <th className="pb-2 font-medium">Weight</th>
                <th className="pb-2 font-medium">Points</th>
              </tr>
            </thead>
            <tbody>
              {breakdown.map((item) => (
                <tr key={item.criterion} className="border-t border-slate-100">
                  <td className="py-2 text-slate-900">
                    {CRITERION_LABELS[item.criterion] ?? item.criterion}
                  </td>
                  <td className="py-2 text-slate-700">{item.rating.toFixed(2)}</td>
                  <td className="py-2 text-slate-700">{item.weight}</td>
                  <td className="py-2 text-slate-700">{item.points.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
