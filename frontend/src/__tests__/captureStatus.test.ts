import {
  deriveCaptureStatus,
  captureStatusView,
  shouldWarnBeforeLeaving,
  type CaptureStatusInput,
} from "@/lib/practice/captureStatus";

function input(over: Partial<CaptureStatusInput>): CaptureStatusInput {
  return {
    mode: "record",
    recorderStatus: "idle",
    uploadStatus: "idle",
    hasSavedAudio: false,
    analysisActive: false,
    analysisFailed: false,
    pasteDirty: false,
    submittingPaste: false,
    ...over,
  };
}

describe("deriveCaptureStatus — record mode", () => {
  it("idle → empty", () => {
    expect(deriveCaptureStatus(input({ recorderStatus: "idle" }))).toBe("empty");
  });
  it("recording/recorded → local-only (not saved)", () => {
    expect(deriveCaptureStatus(input({ recorderStatus: "recording" }))).toBe("local-only");
    expect(deriveCaptureStatus(input({ recorderStatus: "recorded" }))).toBe("local-only");
  });
  it("uploading → uploading; uploaded → saved", () => {
    expect(deriveCaptureStatus(input({ recorderStatus: "uploading" }))).toBe("uploading");
    expect(deriveCaptureStatus(input({ recorderStatus: "uploaded" }))).toBe("saved");
  });
  it("error → error", () => {
    expect(deriveCaptureStatus(input({ recorderStatus: "error" }))).toBe("error");
  });
});

describe("deriveCaptureStatus — upload mode", () => {
  it("file selected (ready) → local-only", () => {
    expect(deriveCaptureStatus(input({ mode: "upload", uploadStatus: "ready" }))).toBe("local-only");
  });
  it("uploading → uploading; uploaded → saved", () => {
    expect(deriveCaptureStatus(input({ mode: "upload", uploadStatus: "uploading" }))).toBe("uploading");
    expect(deriveCaptureStatus(input({ mode: "upload", uploadStatus: "uploaded" }))).toBe("saved");
  });
});

describe("deriveCaptureStatus — paste mode", () => {
  it("dirty draft → local-only; submitting → saving", () => {
    expect(deriveCaptureStatus(input({ mode: "paste", pasteDirty: true }))).toBe("local-only");
    expect(deriveCaptureStatus(input({ mode: "paste", submittingPaste: true }))).toBe("saving");
  });
});

describe("deriveCaptureStatus — analysis precedence", () => {
  it("analysis failed/running wins over saved audio", () => {
    expect(deriveCaptureStatus(input({ hasSavedAudio: true, analysisFailed: true }))).toBe("analysis-failed");
    expect(deriveCaptureStatus(input({ hasSavedAudio: true, analysisActive: true }))).toBe("analysis-running");
  });
  it("saved audio with no analysis → saved", () => {
    expect(deriveCaptureStatus(input({ recorderStatus: "idle", hasSavedAudio: true }))).toBe("saved");
  });
});

describe("captureStatusView — honest copy", () => {
  it("local-only is not safe to leave and never claims saved", () => {
    const v = captureStatusView("local-only");
    expect(v.canSafelyLeave).toBe(false);
    expect(v.tone).toBe("warning");
    expect(v.description.toLowerCase()).toContain("only in this browser");
  });
  it("saved is success + safe to leave", () => {
    const v = captureStatusView("saved");
    expect(v.canSafelyLeave).toBe(true);
    expect(v.tone).toBe("success");
  });
  it("analysis-failed is retryable and reassures the recording is safe", () => {
    const v = captureStatusView("analysis-failed");
    expect(v.retryable).toBe(true);
    expect(v.description.toLowerCase()).toContain("safe");
  });
  it("uploading/saving are not safe to leave", () => {
    expect(captureStatusView("uploading").canSafelyLeave).toBe(false);
    expect(captureStatusView("saving").canSafelyLeave).toBe(false);
  });
});

describe("shouldWarnBeforeLeaving", () => {
  it("warns for in-flight / local-only states only", () => {
    expect(shouldWarnBeforeLeaving("local-only")).toBe(true);
    expect(shouldWarnBeforeLeaving("uploading")).toBe(true);
    expect(shouldWarnBeforeLeaving("saving")).toBe(true);
    expect(shouldWarnBeforeLeaving("saved")).toBe(false);
    expect(shouldWarnBeforeLeaving("empty")).toBe(false);
    expect(shouldWarnBeforeLeaving("analysis-running")).toBe(false);
  });
});
