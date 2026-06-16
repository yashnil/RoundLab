import {
  deriveSpeechWorkspaceView,
  isSafeToLeave,
} from "@/lib/speechWorkspace";

describe("deriveSpeechWorkspaceView", () => {
  it("null status or notFound → not-found", () => {
    expect(deriveSpeechWorkspaceView({ speechStatus: null })).toBe("not-found");
    expect(
      deriveSpeechWorkspaceView({ speechStatus: "done", notFound: true }),
    ).toBe("not-found");
  });

  it("error status → failure (over everything else)", () => {
    expect(
      deriveSpeechWorkspaceView({ speechStatus: "error", hasReport: true }),
    ).toBe("failure");
  });

  it("local upload in flight → uploading", () => {
    expect(
      deriveSpeechWorkspaceView({ speechStatus: "pending", uploadStatus: "uploading" }),
    ).toBe("uploading");
  });

  it("transcribing / analyzing → processing", () => {
    expect(deriveSpeechWorkspaceView({ speechStatus: "transcribing" })).toBe("processing");
    expect(deriveSpeechWorkspaceView({ speechStatus: "analyzing" })).toBe("processing");
  });

  it("done with report → report; done without report stays processing", () => {
    expect(
      deriveSpeechWorkspaceView({ speechStatus: "done", hasReport: true }),
    ).toBe("report");
    expect(
      deriveSpeechWorkspaceView({ speechStatus: "done", hasReport: false }),
    ).toBe("processing");
  });

  it("pending with no media → capture", () => {
    expect(deriveSpeechWorkspaceView({ speechStatus: "pending" })).toBe("capture");
  });

  it("never returns a non-canonical status string", () => {
    const views = (["pending", "transcribing", "analyzing", "done", "error"] as const).map(
      (s) => deriveSpeechWorkspaceView({ speechStatus: s, hasReport: true }),
    );
    views.forEach((v) =>
      expect(["capture", "uploading", "processing", "report", "failure", "not-found"]).toContain(v),
    );
  });
});

describe("isSafeToLeave", () => {
  it("safe only in terminal/report views", () => {
    expect(isSafeToLeave("report")).toBe(true);
    expect(isSafeToLeave("failure")).toBe(true);
    expect(isSafeToLeave("not-found")).toBe(true);
    expect(isSafeToLeave("capture")).toBe(false);
    expect(isSafeToLeave("uploading")).toBe(false);
    expect(isSafeToLeave("processing")).toBe(false);
  });
});
