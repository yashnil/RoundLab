import {
  validateAudioFile,
  classifyUploadError,
  ALLOWED_AUDIO_EXT,
  MAX_AUDIO_BYTES,
} from "@/hooks/useSpeechUpload";

function fakeFile(name: string, size: number): File {
  return { name, size, type: "audio/webm" } as File;
}

describe("validateAudioFile", () => {
  it("accepts an allowed extension within size", () => {
    expect(validateAudioFile(fakeFile("speech.mp3", 1000)).ok).toBe(true);
  });

  it("rejects an unsupported extension", () => {
    const v = validateAudioFile(fakeFile("speech.txt", 1000));
    expect(v.ok).toBe(false);
    expect(v.kind).toBe("unsupported-file");
  });

  it("rejects an empty file", () => {
    const v = validateAudioFile(fakeFile("speech.mp3", 0));
    expect(v.ok).toBe(false);
    expect(v.kind).toBe("empty-file");
  });

  it("rejects a file over the size limit", () => {
    const v = validateAudioFile(fakeFile("speech.wav", MAX_AUDIO_BYTES + 1));
    expect(v.ok).toBe(false);
    expect(v.kind).toBe("file-too-large");
  });

  it("uses the real allowed-extension list", () => {
    expect(ALLOWED_AUDIO_EXT).toContain("mp3");
    expect(ALLOWED_AUDIO_EXT).toContain("m4a");
  });
});

describe("classifyUploadError", () => {
  it("honors an explicit kind tag", () => {
    const e = Object.assign(new Error("boom"), { kind: "storage" as const });
    expect(classifyUploadError(e).kind).toBe("storage");
  });

  it("detects auth expiration from the message", () => {
    expect(classifyUploadError(new Error("401 Unauthorized")).kind).toBe("authentication");
    expect(classifyUploadError(new Error("JWT expired")).kind).toBe("authentication");
  });

  it("detects network failures", () => {
    expect(classifyUploadError(new Error("Failed to fetch")).kind).toBe("network");
  });

  it("falls back to unknown", () => {
    expect(classifyUploadError(new Error("weird")).kind).toBe("unknown");
  });
});
