import { render, screen } from "@testing-library/react";
import { vi, describe, expect, it, beforeEach } from "vitest";

import { SessionTabs } from "@/components/SessionTabs";

const pathname = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => pathname(),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    ...props
  }: React.PropsWithChildren<{ href: string }>) => (
    <a {...props}>{children}</a>
  ),
}));

describe("SessionTabs", () => {
  beforeEach(() => {
    pathname.mockReturnValue("/sessions/session-1/health");
  });

  it("marks the active tab with aria-current", () => {
    render(<SessionTabs sessionId="session-1" />);

    expect(screen.getByRole("link", { name: /context health/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: /timeline/i })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("labels the tab navigation", () => {
    render(<SessionTabs sessionId="session-1" />);

    expect(screen.getByRole("navigation", { name: "Session views" })).toBeInTheDocument();
  });
});
