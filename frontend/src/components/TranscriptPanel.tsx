"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, AlertTriangle, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Transcript } from "@/types";

type Readiness = "too_short" | "low" | "ready";

function readiness(wc: number | null): Readiness {
  if (wc === null || wc < 25) return "too_short";
  if (wc < 75) return "low";
  return "ready";
}

interface TranscriptPanelProps {
  transcript: Transcript;
  transcribing?: boolean;
  onReRecord?: () => void;
}

export default function TranscriptPanel({
  transcript,
  transcribing = false,
  onReRecord,
}: TranscriptPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const level = readiness(transcript.word_count);
  const wc = transcript.word_count ?? 0;

  return (
    <div className="flex flex-col gap-3">
      {/* Row: badge + toggle */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {level === "too_short" && (
            <Badge variant="red" className="gap-1">
              <AlertTriangle size={9} />
              Too short · {wc} words
            </Badge>
          )}
          {level === "low"  && <Badge variant="amber">Limited · {wc} words</Badge>}
          {level === "ready" && <Badge variant="green">Ready · {wc} words</Badge>}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? "Collapse" : "View transcript"}
        </button>
      </div>

      {/* Too-short warning + re-record */}
      {level === "too_short" && (
        <div className="flex items-start gap-3 rounded-lg border border-danger/20 bg-danger/5 px-4 py-3">
          <AlertTriangle size={13} className="mt-0.5 shrink-0 text-danger" />
          <div className="flex flex-1 flex-col gap-2">
            <p className="text-sm text-danger/90">
              Too short for strong feedback. Record at least 30 seconds.
            </p>
            {onReRecord && (
              <button
                type="button"
                onClick={onReRecord}
                disabled={transcribing}
                className="flex w-fit items-center gap-1.5 rounded-md border border-danger/25 bg-danger/10 px-2.5 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/15 disabled:opacity-50"
              >
                <RefreshCw size={10} />
                Delete audio &amp; re-record
              </button>
            )}
          </div>
        </div>
      )}

      {/* Low-confidence warning */}
      {level === "low" && (
        <div className="flex items-start gap-3 rounded-lg border border-warn/20 bg-warn/5 px-4 py-3">
          <AlertTriangle size={13} className="mt-0.5 shrink-0 text-warn" />
          <p className="text-sm text-warn/90">
            Short sample ({wc} words). Analysis will proceed with reduced confidence.
          </p>
        </div>
      )}

      {/* Transcript text */}
      {expanded && (
        <div className="rounded-lg border border-hairline bg-surface-2 p-4">
          <p className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-muted">
            {transcript.text}
          </p>
        </div>
      )}
    </div>
  );
}
