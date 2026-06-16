import {
  deriveProcessingStages,
  processingHeadline,
  isProcessingTerminal,
  ANALYSIS_CATEGORIES,
} from "@/lib/practice/processingStages";

describe("deriveProcessingStages", () => {
  it("queued/running → analysis active, later stages upcoming", () => {
    const s = deriveProcessingStages({ jobStatus: "running", hasReport: false, failed: false });
    expect(s.find((x) => x.id === "input")!.status).toBe("done");
    expect(s.find((x) => x.id === "analysis")!.status).toBe("active");
    expect(s.find((x) => x.id === "assembling")!.status).toBe("upcoming");
    expect(s.find((x) => x.id === "ready")!.status).toBe("upcoming");
  });

  it("succeeded but report not loaded → assembling active", () => {
    const s = deriveProcessingStages({ jobStatus: "succeeded", hasReport: false, failed: false });
    expect(s.find((x) => x.id === "analysis")!.status).toBe("done");
    expect(s.find((x) => x.id === "assembling")!.status).toBe("active");
  });

  it("report loaded → all done", () => {
    const s = deriveProcessingStages({ jobStatus: "succeeded", hasReport: true, failed: false });
    expect(s.every((x) => x.status === "done")).toBe(true);
  });

  it("failed → analysis failed, never marks later stages done", () => {
    const s = deriveProcessingStages({ jobStatus: "failed", hasReport: false, failed: true });
    expect(s.find((x) => x.id === "analysis")!.status).toBe("failed");
    expect(s.find((x) => x.id === "ready")!.status).toBe("upcoming");
  });

  it("never marks a stage done from elapsed time alone (no time input exists)", () => {
    // The model has no time input — proves stages can't be faked by elapsed time.
    const s = deriveProcessingStages({ jobStatus: "running", hasReport: false, failed: false });
    expect(s.filter((x) => x.status === "done")).toHaveLength(1); // only "input secured"
  });
});

describe("processingHeadline", () => {
  it("reflects the active stage / terminal states", () => {
    expect(processingHeadline(deriveProcessingStages({ jobStatus: "running", hasReport: false, failed: false }))).toBe("Analysis running");
    expect(processingHeadline(deriveProcessingStages({ jobStatus: "succeeded", hasReport: true, failed: false }))).toBe("Report ready");
    expect(processingHeadline(deriveProcessingStages({ jobStatus: "failed", hasReport: false, failed: true }))).toContain("didn’t finish");
  });
});

describe("isProcessingTerminal", () => {
  it("true only when complete or failed", () => {
    expect(isProcessingTerminal(deriveProcessingStages({ jobStatus: "running", hasReport: false, failed: false }))).toBe(false);
    expect(isProcessingTerminal(deriveProcessingStages({ jobStatus: "succeeded", hasReport: true, failed: false }))).toBe(true);
    expect(isProcessingTerminal(deriveProcessingStages({ jobStatus: "failed", hasReport: false, failed: true }))).toBe(true);
  });
});

describe("ANALYSIS_CATEGORIES", () => {
  it("names the real debate categories examined", () => {
    expect(ANALYSIS_CATEGORIES).toContain("Clash");
    expect(ANALYSIS_CATEGORIES).toContain("Weighing");
    expect(ANALYSIS_CATEGORIES).toContain("Judge adaptation");
    expect(ANALYSIS_CATEGORIES.length).toBe(7);
  });
});
