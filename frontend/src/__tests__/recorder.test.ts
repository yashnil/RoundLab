import {
  recorderReducer,
  initialRecorderState,
  canHandle,
  hasUnsavedRecording,
  isCapturing,
  formatRecorderClock,
  type RecorderState,
} from "@/lib/recorder";

function run(state: RecorderState, events: Parameters<typeof recorderReducer>[1][]) {
  return events.reduce(recorderReducer, state);
}

const fakeBlob = { size: 10 } as Blob;

describe("recorderReducer — happy path", () => {
  it("idle → ready → recording → recorded → uploaded", () => {
    const s = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "TICK", ms: 3000 },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x", durationMs: 3200 },
      { type: "START_UPLOAD" },
      { type: "UPLOAD_SUCCESS" },
    ]);
    expect(s.status).toBe("uploaded");
    expect(s.blob).toBe(fakeBlob);
    expect(s.durationMs).toBe(3200);
    expect(s.error).toBeNull();
  });
});

describe("recorderReducer — invalid transitions are ignored", () => {
  it("cannot start recording before permission", () => {
    const s = recorderReducer(initialRecorderState, { type: "START_RECORDING" });
    expect(s.status).toBe("idle");
  });

  it("cannot stop when not recording", () => {
    const ready = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
    ]);
    expect(recorderReducer(ready, { type: "STOP_RECORDING" }).status).toBe("ready");
  });

  it("ignores TICK unless recording", () => {
    expect(recorderReducer(initialRecorderState, { type: "TICK", ms: 5 }).durationMs).toBe(0);
  });
});

describe("recorderReducer — failure handling preserves the take", () => {
  it("upload failure returns to recorded and keeps the blob", () => {
    const recorded = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x" },
      { type: "START_UPLOAD" },
      { type: "UPLOAD_FAILURE", message: "Network error" },
    ]);
    expect(recorded.status).toBe("recorded");
    expect(recorded.blob).toBe(fakeBlob);
    expect(recorded.error).toBe("Network error");
    expect(recorded.errorKind).toBe("upload");
  });

  it("permission denied is flagged distinctly", () => {
    const s = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_DENIED", message: "Mic blocked" },
    ]);
    expect(s.status).toBe("error");
    expect(s.errorKind).toBe("permission");
  });

  it("FAIL keeps a captured blob", () => {
    const recorded = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x" },
      { type: "FAIL", message: "Boom" },
    ]);
    expect(recorded.status).toBe("error");
    expect(recorded.blob).toBe(fakeBlob);
  });
});

describe("recorderReducer — playback", () => {
  it("toggles play/stop from recorded", () => {
    let s = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x" },
    ]);
    s = recorderReducer(s, { type: "START_PLAYBACK" });
    expect(s.status).toBe("playing");
    s = recorderReducer(s, { type: "STOP_PLAYBACK" });
    expect(s.status).toBe("recorded");
  });

  it("cannot record and play at once (START_RECORDING ignored while playing)", () => {
    let s = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x" },
      { type: "START_PLAYBACK" },
    ]);
    s = recorderReducer(s, { type: "START_RECORDING" });
    expect(s.status).toBe("playing");
  });
});

describe("RESET", () => {
  it("clears everything back to idle", () => {
    const s = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x" },
      { type: "RESET" },
    ]);
    expect(s).toEqual(initialRecorderState);
  });
});

describe("helpers", () => {
  it("hasUnsavedRecording is true after recording, false once uploaded", () => {
    const recorded = run(initialRecorderState, [
      { type: "REQUEST_PERMISSION" },
      { type: "PERMISSION_GRANTED" },
      { type: "START_RECORDING" },
      { type: "STOP_RECORDING" },
      { type: "RECORDING_READY", blob: fakeBlob, url: "blob:x" },
    ]);
    expect(hasUnsavedRecording(recorded)).toBe(true);
    const uploaded = run(recorded, [{ type: "START_UPLOAD" }, { type: "UPLOAD_SUCCESS" }]);
    expect(hasUnsavedRecording(uploaded)).toBe(false);
  });

  it("isCapturing reflects active mic use", () => {
    expect(isCapturing("recording")).toBe(true);
    expect(isCapturing("stopping")).toBe(true);
    expect(isCapturing("recorded")).toBe(false);
  });

  it("canHandle rejects RECORDING_READY when idle", () => {
    expect(canHandle("idle", { type: "RECORDING_READY", blob: fakeBlob, url: "x" })).toBe(false);
  });
});

describe("formatRecorderClock", () => {
  it("formats ms as mm:ss", () => {
    expect(formatRecorderClock(0)).toBe("00:00");
    expect(formatRecorderClock(5000)).toBe("00:05");
    expect(formatRecorderClock(65000)).toBe("01:05");
    expect(formatRecorderClock(-100)).toBe("00:00");
  });
});
