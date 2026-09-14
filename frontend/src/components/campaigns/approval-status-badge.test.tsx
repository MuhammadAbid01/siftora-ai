import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ApprovalStatusBadge } from "./approval-status-badge";

describe("ApprovalStatusBadge", () => {
  it("renders a human-readable label for each approval status", () => {
    const { rerender } = render(<ApprovalStatusBadge status="pending" />);
    expect(screen.getByText("Pending review")).toBeInTheDocument();

    rerender(<ApprovalStatusBadge status="approved" />);
    expect(screen.getByText("Approved")).toBeInTheDocument();

    rerender(<ApprovalStatusBadge status="rejected" />);
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });
});
