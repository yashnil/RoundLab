import { deriveOverview, deriveBallot, deriveSkills } from "@/lib/reportModel";
import type { FeedbackReport, Speech } from "@/types";

function fb(over: Partial<FeedbackReport>): FeedbackReport {
  return {
    id: "f1",
    speech_id: "s1",
    overall_score: 72,
    scores: { clash: 14, weighing: 9, extensions: 16, drops: 18, judge_adaptation: 12 },
    summary: "Solid case, weak weighing.",
    strengths: ["Clear contention structure"],
    weaknesses: ["No comparative weighing"],
    raw_feedback: {
      decision_logic: "Con wins because weighing was uncontested.",
      dropped_or_undercovered_arguments: ["Opponent's economy turn"],
      weighing_diagnostics: ["No magnitude comparison"],
      top_3_priorities: ["Add weighing on C1"],
      recommendations: ["Run a weighing sprint"],
      scoring_version: "v2",
    },
    created_at: "2026-06-01T00:00:00Z",
    ...over,
  };
}

function speech(over: Partial<Speech>): Speech {
  return {
    id: "s1", user_id: "u1", title: "T", speech_type: "summary", side: "con",
    judge_type: "flow", topic: null, audio_url: "http://a/x.mp3", duration_seconds: 120,
    status: "done", created_at: "", updated_at: "", parent_speech_id: null, source_drill_id: null,
    ...over,
  };
}

describe("deriveOverview", () => {
  it("uses summary as diagnosis and the top priority as reason", () => {
    const o = deriveOverview(fb({}), speech({}));
    expect(o.diagnosis).toBe("Solid case, weak weighing.");
    expect(o.reason).toBe("Add weighing on C1");
    expect(o.strength).toBe("Clear contention structure");
    expect(o.recommendedAction).toBe("Run a weighing sprint");
  });

  it("flags the text-only delivery limitation when there is no audio", () => {
    const o = deriveOverview(fb({}), speech({ audio_url: null }));
    expect(o.limitations.some((l) => l.toLowerCase().includes("delivery"))).toBe(true);
  });

  it("flags a stale rubric", () => {
    const o = deriveOverview(fb({ raw_feedback: { scoring_version: "v1" } }), speech({}));
    expect(o.limitations.some((l) => l.toLowerCase().includes("older rubric"))).toBe(true);
  });
});

describe("deriveBallot", () => {
  it("builds an honest decision path and splits accepted/unresolved", () => {
    const b = deriveBallot(fb({}));
    expect(b.votingIssue).toBe("Add weighing on C1");
    expect(b.accepted).toContain("Clear contention structure");
    expect(b.unresolved).toContain("Opponent's economy turn");
    expect(b.decisionPath[0]).toBe("Offense established");
    expect(b.decisionPath).toContain("Voting issue decided it");
    expect(b.rfd).toContain("uncontested");
  });

  it("marks weighing resolved when the score is high and no diagnostics", () => {
    const b = deriveBallot(fb({
      scores: { clash: 14, weighing: 18, extensions: 16, drops: 18, judge_adaptation: 12 },
      raw_feedback: { weighing_diagnostics: [], top_3_priorities: ["x"] },
    }));
    expect(b.decisionPath).toContain("Weighing resolved the comparison");
  });
});

describe("deriveSkills", () => {
  it("groups the five scored dimensions and picks the weakest as priority", () => {
    const s = deriveSkills(fb({}));
    expect(s.priority?.key).toBe("weighing"); // 9/20 is lowest
    expect(s.insights.find((i) => i.key === "weighing")!.group).toBe("strategy");
    expect(s.insights.find((i) => i.key === "clash")!.group).toBe("engagement");
  });

  it("adds delivery to communication when a score is provided", () => {
    const s = deriveSkills(fb({}), 64);
    const delivery = s.insights.find((i) => i.key === "delivery")!;
    expect(delivery.group).toBe("communication");
    expect(delivery.max).toBe(100);
  });

  it("assigns bands by normalized score", () => {
    const s = deriveSkills(fb({}));
    expect(s.insights.find((i) => i.key === "drops")!.band).toBe("strong"); // 18/20
    expect(s.insights.find((i) => i.key === "weighing")!.band).toBe("weak"); // 9/20
  });
});
