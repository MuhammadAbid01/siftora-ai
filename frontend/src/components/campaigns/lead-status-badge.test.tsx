import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LeadStatusBadge } from "./lead-status-badge";

describe("LeadStatusBadge", () => {
  it("renders a human-readable label for each lead status", () => {
    render(<LeadStatusBadge status="qualified" />);
    expect(screen.getByText("Qualified")).toBeInTheDocument();
  });

  it("distinguishes needs_review from rejected", () => {
    const { rerender } = render(<LeadStatusBadge status="needs_review" />);
    expect(screen.getByText("Needs review")).toBeInTheDocument();

    rerender(<LeadStatusBadge status="rejected" />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });
});
