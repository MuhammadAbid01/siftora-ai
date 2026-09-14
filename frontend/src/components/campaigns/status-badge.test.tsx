import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./status-badge";

describe("StatusBadge", () => {
  it("renders a human-readable label for each campaign status", () => {
    render(<StatusBadge status="draft" />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("labels an approved plan distinctly from a queued run", () => {
    const { rerender } = render(<StatusBadge status="plan_approved" />);
    expect(screen.getByText("Plan approved")).toBeInTheDocument();

    rerender(<StatusBadge status="queued" />);
    expect(screen.getByText("Queued")).toBeInTheDocument();
  });
});
