import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { OutreachDraftCard } from "./outreach-draft-card";
import type { ApprovalResponse } from "@/lib/types/api";

const baseApproval: ApprovalResponse = {
  id: "approval-1",
  draft: {
    id: "draft-1",
    lead_id: "lead-1",
    channel: "email",
    subject: "Quick question for Acme",
    body: "Hi Acme team,\n\nWe noticed...\n\nBest regards",
    version: 1,
    quality_status: "passed",
    evidence_refs: [0],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  lead_id: "lead-1",
  campaign_id: "campaign-1",
  company: { id: "company-1", domain: "acme.example", name: "Acme" },
  lead_status: "qualified",
  lead_score: 92,
  status: "pending",
  reviewer_id: null,
  decided_at: null,
  edited: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("OutreachDraftCard", () => {
  it("enables both approve and reject when pending", () => {
    render(<OutreachDraftCard approval={baseApproval} onUpdated={() => {}} />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
  });

  it("disables approve once already approved", () => {
    render(
      <OutreachDraftCard approval={{ ...baseApproval, status: "approved" }} onUpdated={() => {}} />,
    );
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
  });

  it("disables reject once already rejected", () => {
    render(
      <OutreachDraftCard approval={{ ...baseApproval, status: "rejected" }} onUpdated={() => {}} />,
    );
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
  });

  it("shows the quality and approval badges", () => {
    render(
      <OutreachDraftCard
        approval={{
          ...baseApproval,
          draft: { ...baseApproval.draft, quality_status: "needs_review" },
        }}
        onUpdated={() => {}}
      />,
    );
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Pending review")).toBeInTheDocument();
  });

  it("switches to an editable form when Edit is clicked", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<OutreachDraftCard approval={baseApproval} onUpdated={() => {}} />);

    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("Subject")).toHaveValue(baseApproval.draft.subject);
    expect(screen.getByRole("button", { name: "Save edit" })).toBeInTheDocument();
  });
});
