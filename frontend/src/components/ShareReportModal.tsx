"use client";

/**
 * ShareReportModal — lets a user create, copy, and revoke a share link.
 *
 * Privacy model:
 *  - Links are private by default; not created until the user clicks "Create link".
 *  - Evidence summary is off by default.
 *  - Only the selected sections are visible to the recipient.
 *  - The owner can revoke at any time.
 */

import { useEffect, useRef, useState } from "react";
import {
  Link2, Copy, Check, Trash2, Loader2, ExternalLink, X, Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { logEvent } from "@/lib/analytics";
import { buildShareUrl, copyToClipboard } from "@/lib/reportHelpers";
import type { ShareResponse, CreateShareRequest } from "@/types";

interface IncludeSettings {
  include_feedback: boolean;
  include_flow: boolean;
  include_drills: boolean;
  include_delivery: boolean;
  include_transcript: boolean;
  include_improvement: boolean;
  include_evidence_summary: boolean;
}

type IncludeKey = keyof IncludeSettings;

interface ShareReportModalProps {
  speechId: string;
  userId: string;
  hasImprovement: boolean;
  onClose: () => void;
  onPrint?: () => void;
}

const DEFAULT_SETTINGS: IncludeSettings = {
  include_feedback: true,
  include_flow: true,
  include_drills: true,
  include_delivery: true,
  include_transcript: true,
  include_improvement: true,
  include_evidence_summary: false,
};

const SECTION_META: Array<{
  key: IncludeKey;
  label: string;
  description: string;
  sensitive?: boolean;
}> = [
  {
    key: "include_feedback",
    label: "Judge feedback",
    description: "Score, verdict, priorities, strengths, and weaknesses.",
  },
  {
    key: "include_flow",
    label: "Argument flow",
    description: "Claim, warrant, evidence, and impact for each argument.",
  },
  {
    key: "include_drills",
    label: "Practice drills",
    description: "Recommended drills with prompts and success criteria.",
  },
  {
    key: "include_delivery",
    label: "Delivery coach",
    description: "Pacing, filler words, repetition, and delivery score.",
  },
  {
    key: "include_transcript",
    label: "Transcript",
    description: "Full speech transcript text.",
  },
  {
    key: "include_improvement",
    label: "Improvement comparison",
    description: "Before/after score and delivery deltas from re-recording.",
  },
  {
    key: "include_evidence_summary",
    label: "Evidence risk summary",
    description:
      "Support labels and retrieved snippets. Uploaded files are never shared.",
    sensitive: true,
  },
];

const EXPIRY_OPTIONS = [
  { label: "No expiration", value: null },
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
];

function snapshotSettings(data: ShareResponse): IncludeSettings {
  return {
    include_feedback: data.include_feedback,
    include_flow: data.include_flow,
    include_drills: data.include_drills,
    include_delivery: data.include_delivery,
    include_transcript: data.include_transcript,
    include_improvement: data.include_improvement,
    include_evidence_summary: data.include_evidence_summary,
  };
}

function settingsDiffer(a: IncludeSettings, b: IncludeSettings): boolean {
  return (Object.keys(a) as IncludeKey[]).some((k) => a[k] !== b[k]);
}

export default function ShareReportModal({
  speechId,
  userId,
  hasImprovement,
  onClose,
}: ShareReportModalProps) {
  const [shareData, setShareData] = useState<ShareResponse | null>(null);
  const [savedSettings, setSavedSettings] = useState<IncludeSettings | null>(null);
  const [settings, setSettings] = useState<IncludeSettings>({
    ...DEFAULT_SETTINGS,
    include_improvement: hasImprovement,
  });
  const [expiresInDays, setExpiresInDays] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [revokeConfirm, setRevokeConfirm] = useState(false);
  const [err, setErr] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);

  // Esc to close
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Load existing share on mount
  useEffect(() => {
    let cancelled = false;
    apiFetch<ShareResponse | null>(
      `/speeches/${speechId}/share?user_id=${encodeURIComponent(userId)}`
    )
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setShareData(data);
          const snap = snapshotSettings(data);
          setSettings(snap);
          setSavedSettings(snap);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speechId, userId]);

  async function createOrUpdateShare() {
    setSaving(true);
    setErr("");
    try {
      const body: CreateShareRequest = {
        user_id: userId,
        ...settings,
        expires_in_days: expiresInDays ?? undefined,
      };
      const data = await apiFetch<ShareResponse>(`/speeches/${speechId}/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setShareData(data);
      const snap = snapshotSettings(data);
      setSavedSettings(snap);
      logEvent("share_report_created", userId, { speech_id: speechId });
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to save share link");
    } finally {
      setSaving(false);
    }
  }

  async function handleCopy() {
    if (!shareData) return;
    const url = buildShareUrl(shareData.share_token);
    const ok = await copyToClipboard(url);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
      logEvent("share_report_copied", userId, { speech_id: speechId });
    }
  }

  async function revokeShare() {
    if (!shareData) return;
    setRevoking(true);
    setErr("");
    try {
      await apiFetch(
        `/shared-reports/${shareData.id}?user_id=${encodeURIComponent(userId)}`,
        { method: "DELETE" }
      );
      setShareData(null);
      setSavedSettings(null);
      setRevokeConfirm(false);
      logEvent("share_report_revoked", userId, { speech_id: speechId });
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to revoke link");
    } finally {
      setRevoking(false);
    }
  }

  function toggleKey(key: IncludeKey) {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const shareUrl = shareData ? buildShareUrl(shareData.share_token) : null;
  const hasUnsavedChanges =
    shareData && savedSettings ? settingsDiffer(settings, savedSettings) : false;

  return (
    /* ── Backdrop: dark enough so the report beneath doesn't compete ── */
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center px-0 sm:px-4"
      style={{ backgroundColor: "rgba(0,0,0,0.78)", backdropFilter: "blur(3px)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      data-testid="share-modal-backdrop"
    >
      {/* ── Panel: fully opaque surface-1 (bg-surface was undefined — this fixes it) ── */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Share report"
        className="relative w-full sm:max-w-lg rounded-t-2xl sm:rounded-2xl border border-hairline-strong bg-surface-1 shadow-2xl flex flex-col overflow-hidden max-h-[92vh]"
      >
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between border-b border-hairline px-5 py-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2">
              <Link2 size={14} className="text-lav" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-ink">Share report</h2>
                {shareData && (
                  <span
                    className="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
                    style={{
                      background: "oklch(0.620 0.170 145 / 0.12)",
                      border: "1px solid oklch(0.620 0.170 145 / 0.30)",
                      color: "var(--color-ok)",
                    }}
                  >
                    Active link
                  </span>
                )}
              </div>
              <p className="text-xs text-ink-faint mt-0.5">
                Create a private link for coaches, teammates, or parents.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close share dialog"
            className="mt-0.5 shrink-0 rounded-lg p-1.5 text-ink-faint hover:bg-surface-2 hover:text-ink transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* ── Scrollable body ─────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center py-14">
              <Loader2 size={20} className="animate-spin text-ink-faint" />
            </div>
          ) : (
            <div className="divide-y divide-hairline">

              {/* ── Active link / empty state ──────────────────────────── */}
              <div className="px-5 py-4 flex flex-col gap-3">
                {shareUrl ? (
                  <>
                    {/* Link field */}
                    <div className="flex items-center gap-1.5 rounded-lg border border-hairline bg-surface-2 px-3 py-2.5">
                      <p className="min-w-0 flex-1 truncate font-mono text-xs text-ink-subtle">
                        {shareUrl}
                      </p>
                      <button
                        onClick={handleCopy}
                        title="Copy link"
                        className="shrink-0 flex items-center gap-1 rounded-md px-2 py-1 text-xs text-ink-subtle hover:bg-surface-3 hover:text-ink transition-colors"
                      >
                        {copied ? (
                          <>
                            <Check size={11} className="text-ok" />
                            <span className="text-ok">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={11} />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                      <a
                        href={shareUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open shared view"
                        className="shrink-0 rounded-md p-1.5 text-ink-faint hover:bg-surface-3 hover:text-ink transition-colors"
                      >
                        <ExternalLink size={11} />
                      </a>
                    </div>

                    {/* Revoke */}
                    {!revokeConfirm ? (
                      <button
                        onClick={() => setRevokeConfirm(true)}
                        className="flex w-fit items-center gap-1.5 text-xs text-ink-faint hover:text-danger transition-colors"
                      >
                        <Trash2 size={11} />
                        Revoke link
                      </button>
                    ) : (
                      <div
                        className="flex items-center gap-2 rounded-lg px-3 py-2.5"
                        style={{
                          background: "oklch(0.640 0.215 25 / 0.06)",
                          border: "1px solid oklch(0.640 0.215 25 / 0.25)",
                        }}
                      >
                        <p className="flex-1 text-xs text-ink-subtle">
                          Revoke this link permanently?
                        </p>
                        <button
                          onClick={() => setRevokeConfirm(false)}
                          className="text-xs text-ink-faint hover:text-ink"
                        >
                          Cancel
                        </button>
                        <Button
                          size="sm"
                          variant="destructive"
                          className="h-7 gap-1 px-2.5 text-xs"
                          onClick={revokeShare}
                          disabled={revoking}
                        >
                          {revoking && <Loader2 size={10} className="animate-spin" />}
                          Yes, revoke
                        </Button>
                      </div>
                    )}
                  </>
                ) : (
                  /* Empty state */
                  <div className="flex items-start gap-3 rounded-lg border border-hairline bg-surface-2 px-4 py-3.5">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-hairline bg-surface-3">
                      <Link2 size={12} className="text-ink-faint" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-ink-subtle">
                        No active share link yet
                      </p>
                      <p className="mt-0.5 text-xs text-ink-faint">
                        Create a private link to share the selected report sections.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* ── Section checklist ─────────────────────────────────── */}
              <div className="px-5 py-4">
                <p className="text-eyebrow text-ink-faint mb-3">
                  Include in shared report
                </p>
                <div className="flex flex-col gap-1.5">
                  {SECTION_META.map(({ key, label, description, sensitive }) => {
                    const checked = settings[key];
                    return (
                      <label
                        key={key}
                        className="flex cursor-pointer items-start gap-3 rounded-lg px-3 py-2.5 transition-colors"
                        style={
                          checked
                            ? {
                                background: "oklch(0.510 0.156 278 / 0.07)",
                                border: "1px solid oklch(0.510 0.156 278 / 0.22)",
                              }
                            : {
                                border: "1px solid transparent",
                              }
                        }
                        onMouseEnter={(e) => {
                          if (!checked)
                            (e.currentTarget as HTMLElement).style.background =
                              "var(--color-surface-2)";
                        }}
                        onMouseLeave={(e) => {
                          if (!checked)
                            (e.currentTarget as HTMLElement).style.background = "";
                        }}
                      >
                        <div className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleKey(key)}
                            className="h-3.5 w-3.5 rounded accent-lav"
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-sm font-medium text-ink">
                              {label}
                            </span>
                            {sensitive && (
                              <span className="inline-flex items-center rounded border border-hairline-strong bg-surface-3 px-1 py-0.5 text-[10px] font-medium text-ink-faint">
                                off by default
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 text-xs text-ink-faint leading-relaxed">
                            {description}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* ── Expiration ──────────────────────────────────────────── */}
              <div className="px-5 py-4">
                <p className="text-eyebrow text-ink-faint mb-3">Link expiration</p>
                <div className="flex gap-2 flex-wrap">
                  {EXPIRY_OPTIONS.map(({ label, value }) => {
                    const active = expiresInDays === value;
                    return (
                      <button
                        key={label}
                        onClick={() => setExpiresInDays(value)}
                        className="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                        style={
                          active
                            ? {
                                background: "var(--color-lav)",
                                border: "1px solid var(--color-lav)",
                                color: "oklch(0.975 0.001 264)",
                              }
                            : {
                                border: "1px solid var(--color-hairline-strong)",
                                color: "var(--color-ink-subtle)",
                              }
                        }
                        onMouseEnter={(e) => {
                          if (!active) {
                            (e.currentTarget as HTMLElement).style.borderColor =
                              "oklch(0.510 0.156 278 / 0.5)";
                            (e.currentTarget as HTMLElement).style.color =
                              "var(--color-ink)";
                            (e.currentTarget as HTMLElement).style.background =
                              "var(--color-surface-2)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!active) {
                            (e.currentTarget as HTMLElement).style.borderColor = "";
                            (e.currentTarget as HTMLElement).style.color = "";
                            (e.currentTarget as HTMLElement).style.background = "";
                          }
                        }}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* ── Privacy note ────────────────────────────────────────── */}
              <div className="px-5 py-4">
                <div className="flex items-start gap-3 rounded-lg border border-hairline bg-surface-2 px-4 py-3.5">
                  <Shield size={14} className="mt-0.5 shrink-0 text-ink-faint" />
                  <div>
                    <p className="text-xs font-semibold text-ink-subtle mb-1.5">
                      Privacy controls
                    </p>
                    <p className="text-xs text-ink-faint leading-relaxed">
                      Anyone with this link can view the selected sections. You can
                      revoke the link at any time. Audio recordings and uploaded evidence
                      files are never shared.
                    </p>
                    {settings.include_evidence_summary && (
                      <p className="mt-1.5 text-xs text-ink-faint leading-relaxed">
                        Evidence summary shares only support labels and retrieved snippets
                        — not the original uploaded files.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ──────────────────────────────────────────────────── */}
        {!loading && (
          <div className="flex items-center justify-between border-t border-hairline bg-surface-1 px-5 py-4 shrink-0">
            <p className="text-xs text-ink-faint">
              {hasUnsavedChanges ? "Unsaved changes" : "Changes apply to this link only."}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="rounded-lg border border-hairline px-3 py-1.5 text-xs text-ink-subtle hover:text-ink hover:bg-surface-2 transition-colors"
              >
                Close
              </button>
              <Button
                size="sm"
                className="gap-1.5 px-3 text-xs"
                onClick={createOrUpdateShare}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <Loader2 size={11} className="animate-spin" />
                    {shareData ? "Updating…" : "Creating…"}
                  </>
                ) : (
                  <>
                    <Link2 size={11} />
                    {shareData ? "Update link" : "Create link"}
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* ── Error strip ─────────────────────────────────────────────── */}
        {err && (
          <div className="border-t border-hairline bg-surface-1 px-5 py-3">
            <p className="text-xs text-danger">{err}</p>
          </div>
        )}
      </div>
    </div>
  );
}
