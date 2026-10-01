import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DetectionEventsFilterList } from "@/components/DetectionEventsFilterList";
import type { DetectionEvent } from "@/lib/api/types";

const event: DetectionEvent = {
  id: "event-1",
  session_id: "session-1",
  analysis_run_id: "run-1",
  detection_type: "contradiction",
  severity: "high",
  confidence: 0.8,
  explanation: "The values conflict.",
  timestamp: "2026-01-01T00:00:00Z",
  evidence: [],
  related_message_ids: [],
  metadata: {},
};

describe("DetectionEventsFilterList", () => {
  it("exposes severity controls as pressed buttons", async () => {
    const user = userEvent.setup();
    render(<DetectionEventsFilterList sessionId="session-1" events={[event]} />);

    const high = screen.getByRole("button", { name: /high/i });
    expect(high).toHaveAttribute("aria-pressed", "false");

    await user.click(high);

    expect(high).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("The values conflict.")).toBeInTheDocument();
  });

  it("associates the detection-type select with a label", () => {
    render(<DetectionEventsFilterList sessionId="session-1" events={[event]} />);

    expect(
      screen.getByLabelText("Filter by detection type"),
    ).toHaveValue("all");
  });
});
