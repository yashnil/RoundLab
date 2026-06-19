import {
  isOverdue,
  reviewBacklog,
  assignmentHandoffHref,
  RECIPIENT_STATE_LABEL,
} from "@/lib/assignments";
import type { Assignment, RecipientStatus } from "@/types";

function rec(over: Partial<RecipientStatus>): RecipientStatus {
  return {
    id: "r", user_id: "u", display_name: null, status: "assigned",
    submission_speech_id: null, coach_feedback: null, submitted_at: null, reviewed_at: null,
    ...over,
  };
}

function assignment(over: Partial<Assignment>): Assignment {
  return {
    id: "a", team_id: "t", created_by: "c", title: "Summary rep", kind: "speech",
    speech_type: "summary", side: "con", judge_type: "flow", topic: "Resolved: X",
    goal: "Collapse and weigh", success_criteria: [], due_date: null,
    created_at: "2026-06-18T00:00:00Z", recipients: [],
    ...over,
  };
}

describe("isOverdue", () => {
  it("is false without a due date", () => {
    expect(isOverdue(assignment({ due_date: null }))).toBe(false);
  });
  it("is true when past due and someone is unfinished", () => {
    const a = assignment({ due_date: "2026-06-10", recipients: [rec({ status: "assigned" })] });
    expect(isOverdue(a, new Date("2026-06-18"))).toBe(true);
  });
  it("is false when past due but everyone is reviewed", () => {
    const a = assignment({ due_date: "2026-06-10", recipients: [rec({ status: "reviewed" })] });
    expect(isOverdue(a, new Date("2026-06-18"))).toBe(false);
  });
  it("is false before the due date", () => {
    const a = assignment({ due_date: "2026-06-30", recipients: [rec({ status: "assigned" })] });
    expect(isOverdue(a, new Date("2026-06-18"))).toBe(false);
  });
});

describe("reviewBacklog", () => {
  it("counts only ready-for-review recipients across assignments", () => {
    const a1 = assignment({ recipients: [rec({ status: "ready_for_review" }), rec({ status: "processing" })] });
    const a2 = assignment({ recipients: [rec({ status: "ready_for_review" }), rec({ status: "reviewed" })] });
    expect(reviewBacklog([a1, a2])).toBe(2);
  });

  it("does not count work still processing", () => {
    const a = assignment({ recipients: [rec({ status: "processing" }), rec({ status: "started" })] });
    expect(reviewBacklog([a])).toBe(0);
  });
});

describe("assignmentHandoffHref", () => {
  it("carries speech context + recipient into /session", () => {
    const href = assignmentHandoffHref(assignment({}), "rec-9");
    const params = new URLSearchParams(href.split("?")[1]);
    expect(href.startsWith("/session?")).toBe(true);
    expect(params.get("type")).toBe("summary");
    expect(params.get("judge")).toBe("flow");
    expect(params.get("side")).toBe("con");
    expect(params.get("goal")).toBe("Collapse and weigh");
    expect(params.get("assignment")).toBe("rec-9");
  });
});

describe("RECIPIENT_STATE_LABEL", () => {
  it("labels each effective recipient state", () => {
    expect(RECIPIENT_STATE_LABEL.ready_for_review).toBe("Ready for review");
    expect(RECIPIENT_STATE_LABEL.processing).toBe("Processing");
    expect(RECIPIENT_STATE_LABEL.revision_requested).toBe("Revision requested");
  });
});
