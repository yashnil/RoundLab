"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, ChevronUp, AlertTriangle, RefreshCw, Copy, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { T, EASE } from "@/lib/motion";
import { useCopy } from "@/lib/useCopy";
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
  const [copyText, copied] = useCopy();
  const level = readiness(transcript.word_count);
  const wc = transcript.word_count ?? 0;

  // Estimated speaking time
  const estSecs = Math.round((wc / 120) * 60); // ~120 wpm
  const estLabel = estSecs < 60
    ? `~${estSecs}s`
    : `~${Math.round(estSecs / 60)}m ${estSecs % 60}s`;

  return (
    <div className="flex flex-col gap-3">
      {/* Row: stats + toggle */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          {level === "too_short" && (
            <Badge variant="red" className="gap-1">
              <AlertTriangle size={9} />
              Too short · {wc} words
            </Badge>
          )}
          {level === "low"   && <Badge variant="amber">Short · {wc} words</Badge>}
          {level === "ready" && <Badge variant="green">Ready · {wc} words</Badge>}
          {level === "ready" && (
            <span className="text-xs text-ink-faint">{estLabel} of speech</span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {expanded && (
            <button
              type="button"
              onClick={() => copyText(transcript.text)}
              className="flex items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink"
              title="Copy transcript"
            >
              {copied ? <Check size={11} className="text-ok" /> : <Copy size={11} />}
              {copied ? "Copied" : "Copy"}
            </button>
          )}
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? "Collapse" : "Read transcript"}
          </button>
        </div>
      </div>

      {/* Too-short warning */}
      {level === "too_short" && (
        <div className="flex items-start gap-3 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3">
          <AlertTriangle size={13} className="mt-0.5 shrink-0 text-danger" />
          <div className="flex flex-1 flex-col gap-2">
            <p className="text-sm text-danger/90">
              Too short for strong feedback. Aim for at least 45–60 seconds.
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
        <div className="flex items-start gap-3 rounded-xl border border-warn/20 bg-warn/5 px-4 py-3">
          <AlertTriangle size={13} className="mt-0.5 shrink-0 text-warn" />
          <p className="text-sm text-warn/90">
            Short sample ({wc} words). Analysis will run but confidence may be lower.
          </p>
        </div>
      )}

      {/* Transcript text — readable max-width, generous line-height */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="rounded-xl border border-hairline bg-surface-2 px-5 py-4">
              <p className="max-w-prose whitespace-pre-wrap text-sm leading-7 text-ink-muted">
                {transcript.text}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
