import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EvidenceItem } from "@/lib/types/api";

const TYPE_LABELS: Record<EvidenceItem["type"], string> = {
  fact: "Fact",
  inference: "Inference",
  unknown: "Unknown",
};

const TYPE_VARIANTS: Record<EvidenceItem["type"], BadgeProps["variant"]> = {
  fact: "success",
  inference: "brand",
  unknown: "neutral",
};

export function EvidenceList({ evidence }: { evidence: EvidenceItem[] }) {
  if (evidence.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No evidence was recorded for this lead.
          </p>
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
          <div
            key={index}
            className="border-l-2 border-slate-100 pl-4 last:border-0 last:pb-0 dark:border-slate-800"
          >
            <Badge variant={TYPE_VARIANTS[item.type]} className="mb-1.5">
              {TYPE_LABELS[item.type]}
            </Badge>
            <p className="text-sm text-slate-900 dark:text-slate-100">{item.claim}</p>
            {item.excerpt && (
              <p className="mt-1 text-sm text-slate-500 italic dark:text-slate-400">
                &ldquo;{item.excerpt}&rdquo;
              </p>
            )}
            {item.source_url && (
              <a
                href={item.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
              >
                {item.source_url}
                <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path
                    d="M4 8 8 4M8 4H4.5M8 4v3.5"
                    stroke="currentColor"
                    strokeWidth="1.3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
