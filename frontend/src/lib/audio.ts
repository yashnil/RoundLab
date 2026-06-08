import type { SupabaseClient } from "@supabase/supabase-js";

const AUDIO_BUCKET = "audio";
const SIGNED_URL_EXPIRY_SECONDS = 3600; // 1 hour

/**
 * Resolves a Supabase Storage path to a playable signed URL.
 *
 * - null/undefined → null (no-op, caller skips rendering)
 * - Already an http(s) URL → returned as-is (public bucket or pre-resolved)
 * - Storage path → 1-hour signed URL via the authenticated browser client
 *
 * Returns null if signing fails (e.g. expired session, missing RLS policy).
 * The caller should show an inline error in that case.
 */
export async function resolveAudioUrl(
  pathOrUrl: string | null | undefined,
  supabase: SupabaseClient,
): Promise<string | null> {
  if (!pathOrUrl) return null;
  if (pathOrUrl.startsWith("https://") || pathOrUrl.startsWith("http://")) {
    return pathOrUrl;
  }
  try {
    const { data, error } = await supabase.storage
      .from(AUDIO_BUCKET)
      .createSignedUrl(pathOrUrl, SIGNED_URL_EXPIRY_SECONDS);
    if (error || !data?.signedUrl) return null;
    return data.signedUrl;
  } catch {
    return null;
  }
}
