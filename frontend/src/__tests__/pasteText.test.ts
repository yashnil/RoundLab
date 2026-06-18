import {
  wordCount,
  estimateSpeakingSeconds,
  formatSpeakingTime,
  meetsMinimum,
  derivePasteStats,
  MIN_WORDS,
  WORDS_PER_MINUTE,
  PASTE_DELIVERY_LIMITATION,
} from "@/lib/practice/pasteText";

describe("wordCount", () => {
  it("counts whitespace-delimited words", () => {
    expect(wordCount("one two three")).toBe(3);
    expect(wordCount("  padded   words  ")).toBe(2);
  });

  it("treats empty / whitespace as zero", () => {
    expect(wordCount("")).toBe(0);
    expect(wordCount("   \n  ")).toBe(0);
  });
});

describe("estimateSpeakingSeconds", () => {
  it("uses the PF delivery rate", () => {
    expect(estimateSpeakingSeconds(WORDS_PER_MINUTE)).toBe(60);
    expect(estimateSpeakingSeconds(MIN_WORDS)).toBe(30);
  });
});

describe("formatSpeakingTime", () => {
  it("formats as m:ss with zero-padding", () => {
    expect(formatSpeakingTime(30)).toBe("0:30");
    expect(formatSpeakingTime(90)).toBe("1:30");
    expect(formatSpeakingTime(125)).toBe("2:05");
  });
});

describe("meetsMinimum + derivePasteStats", () => {
  it("requires at least MIN_WORDS", () => {
    const short = Array(MIN_WORDS - 1).fill("w").join(" ");
    const ok = Array(MIN_WORDS).fill("w").join(" ");
    expect(meetsMinimum(short)).toBe(false);
    expect(meetsMinimum(ok)).toBe(true);
  });

  it("reports words still needed to reach the minimum", () => {
    const stats = derivePasteStats("one two three");
    expect(stats.words).toBe(3);
    expect(stats.meetsMinimum).toBe(false);
    expect(stats.wordsToMinimum).toBe(MIN_WORDS - 3);
    expect(stats.speakingTime).toBe(formatSpeakingTime(estimateSpeakingSeconds(3)));
  });

  it("clamps wordsToMinimum to zero once met", () => {
    const long = Array(MIN_WORDS + 50).fill("w").join(" ");
    expect(derivePasteStats(long).wordsToMinimum).toBe(0);
  });
});

describe("delivery limitation copy", () => {
  it("is honest about what text-only analysis cannot judge", () => {
    expect(PASTE_DELIVERY_LIMITATION.toLowerCase()).toContain("audio");
    expect(PASTE_DELIVERY_LIMITATION.toLowerCase()).toContain("filler");
  });
});
