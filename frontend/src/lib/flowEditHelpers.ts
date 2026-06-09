import { ArgumentItem, ArgumentMap, FeedbackReport } from "@/types";

/** Deep-copy an argument list for editing without mutating the original. */
export function initEditArgs(args: ArgumentItem[]): ArgumentItem[] {
  return args.map((a) => ({ ...a, issues: [...(a.issues ?? [])] }));
}

/** Return a new list with a blank argument appended. */
export function addArgument(args: ArgumentItem[]): ArgumentItem[] {
  const blank: ArgumentItem = {
    id: null,
    label: "",
    claim: "",
    warrant: "",
    evidence: null,
    impact: "",
    argument_type: "offense",
    issues: [],
    confidence: null,
  };
  return [...args, blank];
}

/** Return a new list with the argument at `index` removed. */
export function deleteArgument(
  args: ArgumentItem[],
  index: number
): ArgumentItem[] {
  return args.filter((_, i) => i !== index);
}

/** Return a new list with a shallow copy of argument at `index` inserted after it. */
export function duplicateArgument(
  args: ArgumentItem[],
  index: number
): ArgumentItem[] {
  const dupe = { ...args[index], id: null, issues: [...(args[index].issues ?? [])] };
  const next = [...args];
  next.splice(index + 1, 0, dupe);
  return next;
}

/** Return a new list with the argument at `index` merged with `changes`. */
export function updateArgument(
  args: ArgumentItem[],
  index: number,
  changes: Partial<ArgumentItem>
): ArgumentItem[] {
  return args.map((a, i) => (i === index ? { ...a, ...changes } : a));
}

/**
 * True when the user has saved a flow correction more recently than the last
 * coaching regeneration from that correction.
 *
 * Returns false if either argMap or feedback is null, or if the flow has
 * never been corrected, or if coaching was already regenerated after the
 * last correction.
 */
export function isFlowCorrectedAndNeedsRegen(
  argMap: ArgumentMap | null,
  feedback: FeedbackReport | null
): boolean {
  if (!argMap || !feedback) return false;
  if (argMap.source_type !== "user_corrected") return false;
  const correctedAt = argMap.user_corrected_at;
  if (!correctedAt) return false;

  const regenAt = feedback.raw_feedback?.flow_correction_regenerated_at;
  if (!regenAt) return true; // never regenerated after correction

  return new Date(correctedAt) > new Date(regenAt as string);
}
