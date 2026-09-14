import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EvidenceItem } from "@/lib/types/api";

const TYPE_LABELS: Record<EvidenceItem["type"], string> = {
  fact: "Fact",
  inference: "Inference",
  unknown: "Unknown",
};

export function EvidenceList({ evidence }: { evidence: EvidenceItem[] }) {
  if (evidence.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">No evidence was recorded for this lead.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {evidence.map((item, index) => (
          <div key={index} className="border-b border-slate-100 pb-4 last:border-0 last:pb-0">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {TYPE_LABELS[item.type]}
            </p>
            <p className="mt-1 text-sm text-slate-900">{item.claim}</p>
            {item.excerpt && (
              <p className="mt-1 text-sm italic text-slate-500">&ldquo;{item.excerpt}&rdquo;</p>
            )}
            {item.source_url && (
              <a
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-block text-xs text-indigo-600 hover:text-indigo-500"
              >
                {item.source_url}
              </a>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
