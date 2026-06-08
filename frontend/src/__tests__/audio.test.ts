import { resolveAudioUrl } from "../lib/audio";
import type { SupabaseClient } from "@supabase/supabase-js";

function makeSupabase(result: { data: { signedUrl: string } | null; error: Error | null }) {
  return {
    storage: {
      from: () => ({
        createSignedUrl: jest.fn().mockResolvedValue(result),
      }),
    },
  } as unknown as SupabaseClient;
}

describe("resolveAudioUrl", () => {
  it("returns null for null input", async () => {
    const sb = makeSupabase({ data: null, error: null });
    expect(await resolveAudioUrl(null, sb)).toBeNull();
  });

  it("returns null for undefined input", async () => {
    const sb = makeSupabase({ data: null, error: null });
    expect(await resolveAudioUrl(undefined, sb)).toBeNull();
  });

  it("returns null for empty string", async () => {
    const sb = makeSupabase({ data: null, error: null });
    expect(await resolveAudioUrl("", sb)).toBeNull();
  });

  it("returns https URL as-is without calling Supabase", async () => {
    const url = "https://example.supabase.co/storage/v1/object/public/audio/file.webm";
    const createSignedUrl = jest.fn();
    const sb = { storage: { from: () => ({ createSignedUrl }) } } as unknown as SupabaseClient;
    const result = await resolveAudioUrl(url, sb);
    expect(result).toBe(url);
    expect(createSignedUrl).not.toHaveBeenCalled();
  });

  it("returns http URL as-is without calling Supabase", async () => {
    const url = "http://localhost:54321/storage/v1/object/public/audio/test.webm";
    const createSignedUrl = jest.fn();
    const sb = { storage: { from: () => ({ createSignedUrl }) } } as unknown as SupabaseClient;
    const result = await resolveAudioUrl(url, sb);
    expect(result).toBe(url);
    expect(createSignedUrl).not.toHaveBeenCalled();
  });

  it("resolves storage path to signed URL", async () => {
    const signedUrl = "https://sb.co/storage/v1/object/sign/audio/uid/file.webm?token=abc";
    const sb = makeSupabase({ data: { signedUrl }, error: null });
    const result = await resolveAudioUrl("uid/speech/drills/drill/attempt-123.webm", sb);
    expect(result).toBe(signedUrl);
  });

  it("returns null when createSignedUrl returns error", async () => {
    const sb = makeSupabase({ data: null, error: new Error("No policy") });
    const result = await resolveAudioUrl("uid/speech/drills/drill/attempt-123.webm", sb);
    expect(result).toBeNull();
  });

  it("returns null when data has no signedUrl", async () => {
    const sb = makeSupabase({ data: null, error: null });
    const result = await resolveAudioUrl("uid/speech/drills/drill/attempt-123.webm", sb);
    expect(result).toBeNull();
  });

  it("returns null when createSignedUrl throws", async () => {
    const sb = {
      storage: {
        from: () => ({
          createSignedUrl: jest.fn().mockRejectedValue(new Error("Network error")),
        }),
      },
    } as unknown as SupabaseClient;
    const result = await resolveAudioUrl("uid/file.webm", sb);
    expect(result).toBeNull();
  });
});
