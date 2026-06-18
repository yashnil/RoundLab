import { Fragment } from "react";
import { WORKFLOW_STEPS } from "@/lib/marketing";

/**
 * The practice loop as a connected horizontal story: Speak → Flow → Ballot → Drill →
 * Improve. Each node carries a distinct one-liner — no repeated sample artifact.
 */
export default function WorkflowRail() {
  return (
    <ol className="flex flex-col gap-3 md:flex-row md:items-start md:gap-0">
      {WORKFLOW_STEPS.map((step, i) => (
        <Fragment key={step.key}>
          <li className="flex flex-1 items-start gap-3 md:flex-col md:items-center md:text-center">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-lav/40 bg-lav/10 font-mono text-xs font-bold text-lav">
              {i + 1}
            </div>
            <div className="flex flex-col gap-1 md:items-center">
              <p className="text-sm font-semibold text-ink">{step.label}</p>
              <p className="max-w-[16rem] text-xs leading-relaxed text-ink-subtle">
                {step.blurb}
              </p>
            </div>
          </li>
          {i < WORKFLOW_STEPS.length - 1 && (
            <li
              className="ml-4 h-4 w-px shrink-0 bg-hairline-strong md:ml-0 md:mt-4 md:h-px md:w-full md:flex-1"
              aria-hidden
            />
          )}
        </Fragment>
      ))}
    </ol>
  );
}
