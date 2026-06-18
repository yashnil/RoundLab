import { Search, FileText, Quote, Tag, BookMarked, ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Evidence section visual — the provenance trail that distinguishes RoundLab from a
 * generic LLM: Claim → Source → Exact quote → AI tag → Citation → Saved card.
 *
 * The exact quote is marked as untouched source text; the tag is marked AI-proposed.
 * This is the homepage proof of "evidence is never rewritten".
 */

interface Node {
  icon: LucideIcon;
  step: string;
  title: string;
  body: string;
  /** Authorship treatment for the node body. */
  origin: "neutral" | "source" | "ai";
}

const NODES: Node[] = [
  {
    icon: Search,
    step: "Claim",
    title: "What you're proving",
    body: "Carbon pricing cuts industrial emissions.",
    origin: "neutral",
  },
  {
    icon: FileText,
    step: "Source",
    title: "Where it's from",
    body: "Nature Energy · peer-reviewed · 2023",
    origin: "neutral",
  },
  {
    icon: Quote,
    step: "Exact quote",
    title: "Source — unedited",
    body: "“A $40/ton price reduced covered-sector emissions 8.5% within two years.”",
    origin: "source",
  },
  {
    icon: Tag,
    step: "Tag",
    title: "AI-proposed",
    body: "Carbon pricing drives near-term industrial emission cuts.",
    origin: "ai",
  },
  {
    icon: BookMarked,
    step: "Saved",
    title: "Cited card",
    body: "MLA citation + read-aloud highlighting, in your library.",
    origin: "neutral",
  },
];

const originStyle: Record<Node["origin"], string> = {
  neutral: "border-hairline bg-surface-2 text-ink-subtle",
  source: "border-authored-user/40 bg-authored-user/[0.08] text-ink",
  ai: "border-authored-ai/40 bg-authored-ai/[0.08] text-ink",
};

export default function EvidenceProvenanceStrip() {
  return (
    <div className="rounded-2xl border border-hairline bg-surface-1 p-5">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-heading text-ink">Every card keeps its paper trail</p>
          <p className="mt-0.5 text-xs text-ink-subtle">
            Search to saved card — the source quote is never rewritten.
          </p>
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1 text-ink-faint">
            <span className="h-2 w-2 rounded-sm bg-authored-user" aria-hidden /> Source
          </span>
          <span className="flex items-center gap-1 text-ink-faint">
            <span className="h-2 w-2 rounded-sm bg-authored-ai" aria-hidden /> AI
          </span>
        </div>
      </div>

      <ol className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:gap-0">
        {NODES.map((node, i) => {
          const Icon = node.icon;
          return (
            <li key={node.step} className="flex items-stretch lg:flex-1">
              <div
                className={
                  "flex flex-1 flex-col gap-2 rounded-lg border p-3 " +
                  originStyle[node.origin]
                }
              >
                <div className="flex items-center gap-1.5">
                  <Icon size={13} className="shrink-0 text-ink-faint" aria-hidden />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-ink-faint">
                    {node.step}
                  </span>
                  {node.origin === "source" && (
                    <span className="ml-auto rounded border border-authored-user/40 px-1 text-[8px] font-semibold uppercase text-authored-user">
                      Source
                    </span>
                  )}
                  {node.origin === "ai" && (
                    <span className="ml-auto rounded border border-authored-ai/40 px-1 text-[8px] font-semibold uppercase text-authored-ai">
                      AI
                    </span>
                  )}
                </div>
                <p className="text-[11px] font-semibold text-ink">{node.title}</p>
                <p className="text-xs leading-relaxed">{node.body}</p>
              </div>
              {i < NODES.length - 1 && (
                <div
                  className="hidden items-center px-1 text-hairline-strong lg:flex"
                  aria-hidden
                >
                  <ArrowRight size={14} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
