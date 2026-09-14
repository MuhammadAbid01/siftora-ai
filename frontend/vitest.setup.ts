import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// vitest.config.ts doesn't set test.globals, so Testing Library's automatic
// afterEach(cleanup) (which checks for a global `afterEach`) never fires —
// register it explicitly so DOM from one test's render() doesn't leak into
// the next (this only bit once a test file rendered the same text/role in
// more than one `it()` block — see outreach-draft-card.test.tsx).
afterEach(() => {
  cleanup();
});
