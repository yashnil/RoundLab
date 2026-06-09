import {
  getPacingBandDisplay,
  getFlagDisplay,
  deliveryScoreColor,
  formatWpm,
  formatFillerBreakdown,
  deriveDeliveryCoachNote,
  deriveDeliveryFocus,
  segmentFlagColor,
} from "@/lib/deliveryHelpers";
import type { DeliveryMetrics } from "@/types";

// ── Factory ────────────────────────────────────────────────────────────────────

function makeMetrics(overrides: Partial<DeliveryMetrics> = {}): DeliveryMetrics {
  return {
    speech_id: "s1",
    user_id: "u1",
    word_count: 200,
    duration_seconds: 90,
    words_per_minute: 133,
    filler_word_count: 2,
    filler_words_json: { um: 1, uh: 1 },
    repeated_phrases_json: [],
    long_sentence_count: 1,
    average_sentence_words: 15,
    delivery_score: 80,
    pacing_band: "steady",
    clarity_flags_json: [],
    timeline_json: [],
    ...overrides,
  };
}

// ── getPacingBandDisplay ───────────────────────────────────────────────────────

describe("getPacingBandDisplay", () => {
  it("returns steady label for steady band", () => {
    const d = getPacingBandDisplay("steady");
    expect(d.label).toBe("Steady");
    expect(d.colorClass).toContain("ok");
  });

  it("returns too fast label for too_fast band", () => {
    const d = getPacingBandDisplay("too_fast");
    expect(d.label).toBe("Too fast");
    expect(d.colorClass).toContain("danger");
  });

  it("returns too slow label for too_slow band", () => {
    const d = getPacingBandDisplay("too_slow");
    expect(d.label).toBe("Too slow");
    expect(d.colorClass).toContain("warn");
  });

  it("returns unknown for null", () => {
    const d = getPacingBandDisplay(null);
    expect(d.label).toBe("Unknown");
  });

  it("returns unknown for undefined", () => {
    const d = getPacingBandDisplay(undefined);
    expect(d.label).toBe("Unknown");
  });

  it("each band has a non-empty hint", () => {
    for (const band of ["steady", "too_fast", "too_slow", "unknown"] as const) {
      expect(getPacingBandDisplay(band).hint.length).toBeGreaterThan(0);
    }
  });
});

// ── getFlagDisplay ─────────────────────────────────────────────────────────────

describe("getFlagDisplay", () => {
  it("returns danger severity for too_fast", () => {
    expect(getFlagDisplay("too_fast").severity).toBe("danger");
  });

  it("returns warn severity for too_slow", () => {
    expect(getFlagDisplay("too_slow").severity).toBe("warn");
  });

  it("returns danger severity for many_fillers", () => {
    expect(getFlagDisplay("many_fillers").severity).toBe("danger");
  });

  it("returns warn for repetitive_wording", () => {
    expect(getFlagDisplay("repetitive_wording").severity).toBe("warn");
  });

  it("returns label for unknown flag", () => {
    const d = getFlagDisplay("some_custom_flag");
    expect(d.label).toBe("some custom flag");
  });
});

// ── deliveryScoreColor ─────────────────────────────────────────────────────────

describe("deliveryScoreColor", () => {
  it("returns ok color for score >= 75", () => {
    expect(deliveryScoreColor(80)).toContain("ok");
    expect(deliveryScoreColor(75)).toContain("ok");
  });

  it("returns warn color for score 50-74", () => {
    expect(deliveryScoreColor(60)).toContain("warn");
    expect(deliveryScoreColor(50)).toContain("warn");
  });

  it("returns danger color for score < 50", () => {
    expect(deliveryScoreColor(30)).toContain("danger");
  });

  it("returns faint for null", () => {
    expect(deliveryScoreColor(null)).toContain("faint");
  });

  it("returns faint for undefined", () => {
    expect(deliveryScoreColor(undefined)).toContain("faint");
  });
});

// ── formatWpm ─────────────────────────────────────────────────────────────────

describe("formatWpm", () => {
  it("formats a WPM value as integer with WPM suffix", () => {
    expect(formatWpm(133.4)).toBe("133 WPM");
  });

  it("rounds to integer", () => {
    expect(formatWpm(149.9)).toBe("150 WPM");
  });

  it("returns dash for null", () => {
    expect(formatWpm(null)).toBe("—");
  });

  it("returns dash for undefined", () => {
    expect(formatWpm(undefined)).toBe("—");
  });
});

// ── formatFillerBreakdown ──────────────────────────────────────────────────────

describe("formatFillerBreakdown", () => {
  it("returns sorted entries by count descending", () => {
    const result = formatFillerBreakdown({ um: 5, uh: 2, like: 8 });
    expect(result[0].word).toBe("like");
    expect(result[0].count).toBe(8);
    expect(result[1].count).toBe(5);
  });

  it("caps at 6 entries", () => {
    const json: Record<string, number> = {};
    for (let i = 0; i < 10; i++) json[`word${i}`] = i;
    const result = formatFillerBreakdown(json);
    expect(result.length).toBeLessThanOrEqual(6);
  });

  it("returns empty array for null", () => {
    expect(formatFillerBreakdown(null)).toEqual([]);
  });

  it("returns empty array for empty object", () => {
    expect(formatFillerBreakdown({})).toEqual([]);
  });
});

// ── deriveDeliveryCoachNote ────────────────────────────────────────────────────

describe("deriveDeliveryCoachNote", () => {
  it("mentions WPM when too_fast flag present", () => {
    const metrics = makeMetrics({
      clarity_flags_json: ["too_fast"],
      words_per_minute: 210,
    });
    const note = deriveDeliveryCoachNote(metrics);
    expect(note).not.toBeNull();
    expect(note).toContain("210 WPM");
  });

  it("mentions filler count when many_fillers flag present", () => {
    const metrics = makeMetrics({
      clarity_flags_json: ["many_fillers"],
      filler_word_count: 15,
      word_count: 100,
    });
    const note = deriveDeliveryCoachNote(metrics);
    expect(note).not.toBeNull();
    expect(note).toContain("15 filler");
  });

  it("mentions repeated phrase when repetitive_wording flag present", () => {
    const metrics = makeMetrics({
      clarity_flags_json: ["repetitive_wording"],
      repeated_phrases_json: [{ phrase: "economic growth", count: 5 }],
    });
    const note = deriveDeliveryCoachNote(metrics);
    expect(note).not.toBeNull();
    expect(note).toContain("economic growth");
  });

  it("returns positive note for high delivery score with no flags", () => {
    const metrics = makeMetrics({ clarity_flags_json: [], delivery_score: 85 });
    const note = deriveDeliveryCoachNote(metrics);
    expect(note).not.toBeNull();
    expect(note!.toLowerCase()).toContain("strong");
  });

  it("returns null when no notable issues and score below 80", () => {
    const metrics = makeMetrics({ clarity_flags_json: [], delivery_score: 70 });
    const note = deriveDeliveryCoachNote(metrics);
    expect(note).toBeNull();
  });
});

// ── deriveDeliveryFocus ────────────────────────────────────────────────────────

describe("deriveDeliveryFocus", () => {
  it("returns slow down text for too_fast", () => {
    const focus = deriveDeliveryFocus(makeMetrics({ clarity_flags_json: ["too_fast"] }));
    expect(focus).toContain("Slow down");
  });

  it("returns reduce filler text for many_fillers", () => {
    const focus = deriveDeliveryFocus(makeMetrics({ clarity_flags_json: ["many_fillers"] }));
    expect(focus).toContain("filler");
  });

  it("returns repetition text for repetitive_wording", () => {
    const focus = deriveDeliveryFocus(makeMetrics({ clarity_flags_json: ["repetitive_wording"] }));
    expect(focus).toContain("phrase");
  });

  it("returns null when no flags", () => {
    const focus = deriveDeliveryFocus(makeMetrics({ clarity_flags_json: [] }));
    expect(focus).toBeNull();
  });
});

// ── segmentFlagColor ───────────────────────────────────────────────────────────

describe("segmentFlagColor", () => {
  it("returns danger class when both flags present", () => {
    const cls = segmentFlagColor(["high_fillers", "repetitive"]);
    expect(cls).toContain("danger");
  });

  it("returns warn class for high_fillers only", () => {
    const cls = segmentFlagColor(["high_fillers"]);
    expect(cls).toContain("warn");
  });

  it("returns lav class for repetitive only", () => {
    const cls = segmentFlagColor(["repetitive"]);
    expect(cls).toContain("lav");
  });

  it("returns hairline class for no flags", () => {
    const cls = segmentFlagColor([]);
    expect(cls).toContain("hairline");
  });
});
