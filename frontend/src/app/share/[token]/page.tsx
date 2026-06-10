"use client";

/**
 * Public shared report page — no login required.
 *
 * Fetches GET /shared-reports/{token} and renders CoachReportView.
 * Shows a polite unavailable state if the token is expired or revoked.
 */

import { useEffect, useState } from "react";
import { Printer, AlertTriangle, Loader2 } from "lucide-react";
import { use } from "react";
import CoachReportView from "@/components/CoachReportView";
import { logEvent } from "@/lib/analytics";
import { speechTypeLabel } from "@/lib/reportHelpers";
import type { SharedReportPayload } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Props {
  params: Promise<{ token: string }>;
}

export default function SharedReportPage({ params }: Props) {
  const { token } = use(params);

  const [data, setData] = useState<SharedReportPayload | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "unavailable" | "error">("loading");
  const [unavailableReason, setUnavailableReason] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(`${API_URL}/shared-reports/${encodeURIComponent(token)}`);
        if (cancelled) return;

        if (res.status === 410 || res.status === 404) {
          const body = await res.json().catch(() => ({}));
          setUnavailableReason(body.detail ?? "This report link is no longer available.");
          setStatus("unavailable");
          return;
        }
        if (!res.ok) {
          setUnavailableReason("Something went wrong loading this report.");
          setStatus("error");
          return;
        }

        const payload: SharedReportPayload = await res.json();
        setData(payload);
        setStatus("ok");
        logEvent("shared_report_opened", undefined, { token });
      } catch {
        if (!cancelled) setStatus("error");
      }
    }

    load();
    return () => { cancelled = true; };
  }, [token]);

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 size={22} className="animate-spin text-ink-faint" />
      </div>
    );
  }

  // ── Unavailable / expired / revoked ─────────────────────────────────────────
  if (status === "unavailable" || status === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
        <AlertTriangle size={32} className="text-ink-faint" />
        <h1 className="text-xl font-semibold text-ink">Report unavailable</h1>
        <p className="max-w-sm text-sm text-ink-subtle leading-relaxed">
          {unavailableReason || "This report link has expired or been revoked. Ask the owner for a new link."}
        </p>
        <a
          href="/"
          className="mt-2 text-sm text-lav underline-offset-2 hover:underline"
        >
          Go to RoundLab
        </a>
      </div>
    );
  }

  if (!data) return null;

  // ── Report ───────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-background print:bg-white">
      {/* Minimal public header — no auth nav */}
      <header className="border-b border-hairline bg-surface px-6 py-3 flex items-center justify-between no-print print:hidden">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-ink">RoundLab</span>
          <span className="text-xs text-ink-faint">
            Shared report · {speechTypeLabel(data.speech_type)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              logEvent("report_print_clicked");
              window.print();
            }}
            className="no-print flex items-center gap-1.5 rounded-md border border-hairline bg-surface px-3 py-1.5 text-xs font-medium text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <Printer size={12} />
            Print / Save as PDF
          </button>
          <a
            href="/"
            className="no-print text-xs text-ink-faint underline-offset-2 hover:underline"
          >
            Try RoundLab
          </a>
        </div>
      </header>

      <CoachReportView data={data} />
    </div>
  );
}
