import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Nav } from "./nav";

describe("Nav", () => {
  it("opens and closes the mobile menu when the toggle is clicked", async () => {
    const user = userEvent.setup();
    render(<Nav />);

    const toggle = screen.getByRole("button", { name: /open menu/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);

    expect(screen.getByRole("button", { name: /close menu/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("navigation", { name: /mobile/i })).toBeInTheDocument();
  });

  it("renders the primary Start Campaign call to action", () => {
    render(<Nav />);
    expect(screen.getAllByRole("link", { name: /start campaign/i }).length).toBeGreaterThan(0);
  });
});
