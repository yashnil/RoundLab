import { Progress } from "@/components/ui/progress";
import type { FeedbackScores, ScoreExplanation } from "@/types";

// Speech-type-specific dimension configurations
const SPEECH_TYPE_DIMS: Record<string, { key: keyof FeedbackScores; label: string; description: string; advice: string }[]> = {
  constructive: [
    { key: "clash", label: "Case Structure", description: "Organization and signposting", advice: "Improve roadmap clarity and logical flow between contentions." },
    { key: "drops", label: "Evidence Use", description: "Source quality and interpretation", advice: "Cite sources clearly and explain what the evidence proves." },
    { key: "weighing", label: "Impact Development", description: "Explains harm and why it matters", advice: "Explain magnitude, probability, and timeframe of your impacts." },
    { key: "extensions", label: "Clarity", description: "Accessible to the judge", advice: "Use clearer language and avoid excessive jargon." },
    { key: "judge_adaptation", label: "Warranting", description: "Complete claim→warrant→evidence→impact chains", advice: "Explain WHY your claims are true, not just assert them." },
  ],
  rebuttal: [
    { key: "clash", label: "Clash & Refutation", description: "Direct engagement with opponent arguments", advice: "Attack specific links and warrants, not just their conclusion." },
    { key: "drops", label: "Coverage", description: "Addressing key opponent offense", advice: "Cover their most important arguments, don't waste time on minor points." },
    { key: "extensions", label: "Response Quality", description: "Clear turns and takeouts", advice: "Explain why your responses matter and how they affect the flow." },
    { key: "judge_adaptation", label: "Evidence Comparison", description: "Comparing source quality", advice: "Compare evidence credibility and explain why yours is better." },
    { key: "weighing", label: "Strategic Framing", description: "Early weighing and offense preservation", advice: "Start framing the ballot and preserve your key offense for later." },
  ],
  summary: [
    { key: "extensions", label: "Extension Quality", description: "Complete extensions with all components", advice: "Extend claim, warrant, evidence, AND impact—not just 'extend our contention.'" },
    { key: "drops", label: "Collapse Strategy", description: "Focusing on most important arguments", advice: "Don't go for everything—collapse to your strongest offense." },
    { key: "clash", label: "Frontlining", description: "Answering key responses and turns", advice: "Address major turns against your offense, don't leave them unanswered." },
    { key: "weighing", label: "Weighing", description: "Explicit impact comparison", advice: "Compare magnitude, probability, timeframe—explain why you outweigh." },
    { key: "judge_adaptation", label: "Judge Clarity", description: "Clear roadmap and organization", advice: "Give the judge a clear ballot direction with organized presentation." },
  ],
  final_focus: [
    { key: "extensions", label: "Ballot Story & Voters", description: "1-2 clear reasons to vote for your side", advice: "Tell the judge exactly why you win with focused voters." },
    { key: "weighing", label: "Comparative Weighing", description: "Explicit impact comparison", advice: "Use magnitude, probability, timeframe to prove you outweigh." },
    { key: "clash", label: "Crystallization", description: "Narrowing to decisive issues", advice: "Focus on what matters most, resolve key clash, don't rehash everything." },
    { key: "drops", label: "Consistency", description: "Following summary, no new arguments", advice: "Stay consistent with summary and don't introduce new arguments." },
    { key: "judge_adaptation", label: "Judge Adaptation", description: "Clear for lay, precise for flow", advice: "Adapt your closing to the judge's preferences and style." },
  ],
};

const DEFAULT_DIMS: { key: keyof FeedbackScores; label: string; description: string; advice: string }[] = [
  { key: "clash", label: "Clash", description: "Engaging opponent arguments", advice: "Directly address opponent claims." },
  { key: "weighing", label: "Weighing", description: "Impact comparison", advice: "Compare impacts on magnitude, probability, timeframe." },
  { key: "extensions", label: "Extensions", description: "Building on arguments", advice: "Develop arguments with new warrants or evidence." },
  { key: "drops", label: "Coverage", description: "Addressing key arguments", advice: "Cover important arguments without gaps." },
  { key: "judge_adaptation", label: "Judge Adapt.", description: "Tailoring to judge", advice: "Adapt strategy to judge preferences." },
];

const SPEECH_TYPE_PURPOSE: Record<string, string> = {
  constructive: "Lay the foundation for your case with clear contentions, warrants, evidence, and impacts.",
  rebuttal: "Answer and attack the opponent's constructive while preserving your offense.",
  summary: "Collapse the round, extend key offense, frontline responses, and weigh impacts.",
  final_focus: "Crystallize the ballot with 1-2 clear voters and explicit weighing.",
};

function barColor(pct: number): string {
  if (pct >= 70) return "bg-lav";
  if (pct >= 50) return "bg-warn";
  return "bg-danger";
}

function normalizeSpeechType(speechType?: string): string | undefined {
  if (!speechType) return undefined;
  const normalized = speechType.toLowerCase().replace(/[_\s]/g, '');
  // Map variations to standard types
  if (normalized.includes('construct')) return 'constructive';
  if (normalized.includes('rebut')) return 'rebuttal';
  if (normalized.includes('summar')) return 'summary';
  if (normalized.includes('final') || normalized.includes('focus')) return 'final_focus';
  if (normalized.includes('cross')) return 'crossfire';
  return speechType.toLowerCase();
}

export default function ScoreBreakdown({
  scores,
  speechType,
  scoreExplanations
}: {
  scores: FeedbackScores;
  speechType?: string;
  scoreExplanations?: ScoreExplanation[];
}) {
  // Get speech-type-specific dimensions
  const normalizedType = normalizeSpeechType(speechType);
  const dims = normalizedType ? (SPEECH_TYPE_DIMS[normalizedType] || DEFAULT_DIMS) : DEFAULT_DIMS;
  const purpose = normalizedType ? SPEECH_TYPE_PURPOSE[normalizedType] : null;

  // Find lowest scoring dimension
  const lowestDim = dims.reduce((lowest, dim) =>
    scores[dim.key] < scores[lowest.key] ? dim : lowest
  , dims[0]);

  // Helper to find explanation for a dimension
  const getExplanation = (dimLabel: string): ScoreExplanation | undefined => {
    if (!scoreExplanations) return undefined;
    // Try to match by dimension name (case insensitive, ignoring spaces/underscores)
    const normalized = dimLabel.toLowerCase().replace(/[_\s&]/g, '');
    return scoreExplanations.find(exp =>
      exp.dimension_name.toLowerCase().replace(/[_\s&]/g, '').includes(normalized) ||
      normalized.includes(exp.dimension_name.toLowerCase().replace(/[_\s&]/g, ''))
    );
  };

  // Clean score band label by removing numeric ranges (e.g., "Functional 12-15" → "Functional")
  const cleanScoreBand = (band: string): string => {
    return band.replace(/\s*\d+[-–]\d+\s*/g, '').trim();
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Speech Type Purpose */}
      {purpose && (
        <div className="rounded-lg border border-lav/10 bg-lav/5 px-3 py-2">
          <p className="text-xs font-medium text-lav mb-1">
            What a {speechType?.replace('_', ' ')} is supposed to do:
          </p>
          <p className="text-xs leading-relaxed text-ink">
            {purpose}
          </p>
        </div>
      )}

      {/* Rubric Label */}
      {speechType && (
        <p className="text-xs text-ink-faint">
          Rubric: <span className="font-medium text-ink-subtle capitalize">{speechType.replace('_', ' ')}</span> Speech
        </p>
      )}

      {/* Score Bars */}
      {dims.map(({ key, label, description, advice }, i) => {
        const value = scores[key];
        const pct   = (value / 20) * 100;
        const explanation = getExplanation(label);

        return (
          <div key={key} className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <span className="w-32 shrink-0 text-sm text-ink-subtle" title={description}>
                {label}
              </span>
              <Progress
                value={value}
                max={20}
                colorClass={barColor(pct)}
                animated
                animationDelay={0.1 + i * 0.08}
                className="h-1"
              />
              <span className="w-10 text-right text-xs font-semibold tabular-nums text-ink-muted">
                {value}/20
              </span>
            </div>

            {/* Show explanation if available, otherwise show generic advice for lowest dimension */}
            {explanation ? (
              <div className="ml-32 flex flex-col gap-1 text-xs">
                <p className="text-ink-faint">
                  <span className="font-medium text-ink-subtle">{cleanScoreBand(explanation.score_band)}:</span> {explanation.evidence_from_speech}
                </p>
                {pct < 70 && (
                  <p className="text-amber">
                    ⚠ To improve: {explanation.how_to_improve}
                  </p>
                )}
              </div>
            ) : (
              key === lowestDim.key && pct < 70 && (
                <p className="ml-32 text-xs leading-relaxed text-amber">
                  ⚠ {advice}
                </p>
              )
            )}
          </div>
        );
      })}

      {/* Dimension Explanations */}
      <div className="flex flex-col gap-1 border-t border-hairline pt-2 text-xs text-ink-faint">
        <p className="font-medium text-ink-subtle">What these dimensions measure for {speechType?.replace('_', ' ')}:</p>
        {dims.map(({ label, description }) => (
          <p key={label}>
            <span className="font-medium text-ink">{label}:</span> {description}
          </p>
        ))}
      </div>
    </div>
  );
}
