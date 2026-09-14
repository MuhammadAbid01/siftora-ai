import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QualityStatusBadge } from "./quality-status-badge";

describe("QualityStatusBadge", () => {
  it("renders a passing label", () => {
    render(<QualityStatusBadge status="passed" />);
    expect(screen.getByText("Quality check passed")).toBeInTheDocument();
  });

  it("renders a needs_review label", () => {
    render(<QualityStatusBadge status="needs_review" />);
    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });
});
