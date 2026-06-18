"use client";

import { FileText, Link2, FlaskConical, Zap, Scale, Gavel, Target, MessageSquare } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface DebateAnatomyProps {
  /** When true, the engine shows a subtle motion-safe "assembling" accent. */
  active?: boolean;
  /** Number of arguments detected so far (real partial data), if known. */
  argumentsFound?: number | null;
}

interface AnatomyNode {
  id: string;
  label: string;
  icon: LucideIcon;
}

const CHAIN: AnatomyNode[] = [
  { id: "claim", label: "Claim", icon: Link2 },
  { id: "warrant", label: "Warrant", icon: Link2 },
  { id: "evidence", label: "Evidence", icon: FlaskConical },
  { id: "impact", label: "Impact", icon: Zap },
];

const TERMINAL: AnatomyNode[] = [
  { id: "weighing", label: "Weighing", icon: Scale },
  { id: "judge", label: "Judge evaluation", icon: Gavel },
  { id: "drill", label: "Drill target", icon: Target },
];

function NodeBox({ node, accent }: { node: AnatomyNode; accent: boolean }) {
  const Icon = node.icon;
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5",
        accent
          ? "border-lav/40 bg-lav/[0.07] text-ink motion-safe:animate-pulse"
          : "border-hairline bg-surface-1 text-ink-subtle",
      )}
    >
      <Icon size={13} className={accent ? "text-lav" : "text-ink-faint"} aria-hidden />
      <span className="text-xs font-medium">{node.label}</span>
    </div>
  );
}

/**
 * Debate-anatomy visualization for the processing room — an explanatory map of
 * how RoundLab assembles a flow from the transcript. It does NOT fabricate
 * argument text or claim per-stage backend telemetry; the `active` accent only
 * signals that analysis is in flight. Vertical on mobile, branched on desktop.
 */
export default function DebateAnatomy({ active = false, argumentsFound }: DebateAnatomyProps) {
  return (
    <figure className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2/40 p-4">
      <figcaption className="flex items-center justify-between">
        <span className="text-eyebrow text-ink-faint">RoundLab&apos;s argument engine</span>
        {argumentsFound != null && argumentsFound > 0 && (
          <span className="text-[10px] text-ink-faint">
            {argumentsFound} argument{argumentsFound !== 1 ? "s" : ""} detected
          </span>
        )}
      </figcaption>

      {/* Transcript entry */}
      <div className="flex items-center gap-2">
        <div className={cn("flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5", active ? "border-lav/40 bg-lav/[0.07]" : "border-hairline bg-surface-1")}>
          <FileText size={13} className={active ? "text-lav" : "text-ink-faint"} aria-hidden />
          <span className="text-xs font-medium text-ink">Transcript</span>
        </div>
        <span className="h-px flex-1 bg-hairline-strong" aria-hidden />
      </div>

      {/* Claim → Warrant → Evidence → Impact (chain) */}
      <div className="flex flex-col gap-1.5 border-l-2 border-hairline pl-3 sm:flex-row sm:items-center sm:gap-2 sm:border-l-0 sm:pl-0">
        {CHAIN.map((node, i) => (
          <div key={node.id} className="flex items-center gap-2 sm:contents">
            <NodeBox node={node} accent={active} />
            {i < CHAIN.length - 1 && (
              <span className="hidden text-hairline-strong sm:inline" aria-hidden>→</span>
            )}
          </div>
        ))}
        {/* Response branch */}
        <div className="flex items-center gap-1.5 sm:ml-2">
          <span className="text-hairline-strong sm:hidden" aria-hidden>↕</span>
          <span className="hidden text-hairline-strong sm:inline" aria-hidden>↕</span>
          <NodeBox node={{ id: "response", label: "Response", icon: MessageSquare }} accent={active} />
        </div>
      </div>

      {/* Terminal chain: weighing → judge → drill */}
      <div className="flex flex-col gap-1.5 border-l-2 border-hairline pl-3 sm:flex-row sm:items-center sm:gap-2 sm:border-l-0 sm:pl-0">
        {TERMINAL.map((node, i) => (
          <div key={node.id} className="flex items-center gap-2 sm:contents">
            <NodeBox node={node} accent={active && node.id === "drill"} />
            {i < TERMINAL.length - 1 && (
              <span className="hidden text-hairline-strong sm:inline" aria-hidden>→</span>
            )}
          </div>
        ))}
      </div>

      <p className="text-[11px] leading-relaxed text-ink-faint">
        This is the structure RoundLab maps from your speech — not a live progress bar. Your
        flow, ballot, and drill target are assembled together, then shown when ready.
      </p>
    </figure>
  );
}
