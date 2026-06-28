"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CheckCircle, ChevronRight } from "lucide-react";
import { EXPERIENCE_LABEL } from "@/types/training";
import type { ExperienceLevel } from "@/types/training";

const RATED_SKILLS = [
  { id: "warranting", label: "Building arguments (claim + reason + impact)" },
  { id: "evidence_use", label: "Using evidence to support claims" },
  { id: "responses", label: "Responding to opponent arguments" },
  { id: "weighing", label: "Comparing impacts to show why you win" },
  { id: "clarity", label: "Speaking clearly and confidently" },
];

interface Props {
  onComplete: (experienceLevel: ExperienceLevel, intakeData: Record<string, unknown>) => void;
  loading?: boolean;
}

export function DiagnosticIntake({ onComplete, loading }: Props) {
  const [step, setStep] = useState<"experience" | "ratings" | "confirm">("experience");
  const [level, setLevel] = useState<ExperienceLevel | null>(null);
  const [ratings, setRatings] = useState<Record<string, number>>({});

  const levels: ExperienceLevel[] = ["first_time", "novice", "jv", "varsity"];

  function handleSubmit() {
    if (!level) return;
    onComplete(level, { self_ratings: ratings });
  }

  const steps = ["experience", "ratings", "confirm"] as const;

  return (
    <div className="max-w-xl mx-auto space-y-6 px-4 py-8">
      <div>
        <h1 className="text-xl font-bold text-ink">Where do you start?</h1>
        <p className="text-[13px] text-ink-subtle mt-1">
          Answer honestly — Dissio uses this to build your personal training plan.
        </p>
      </div>

      {/* Step indicators */}
      <div className="flex gap-2 items-center">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${
                step === s
                  ? "bg-lav text-white"
                  : i < steps.indexOf(step)
                  ? "bg-ok/20 text-ok"
                  : "bg-surface-3 text-ink-faint"
              }`}
            >
              {i + 1}
            </div>
            {i < 2 && <div className="w-6 h-px bg-hairline" />}
          </div>
        ))}
      </div>

      {/* Step: Experience */}
      {step === "experience" && (
        <div className="space-y-3">
          <p className="text-[14px] font-semibold text-ink">How would you describe your debate experience?</p>
          {levels.map((l) => (
            <button
              key={l}
              onClick={() => setLevel(l)}
              className={`w-full text-left rounded-xl border px-4 py-3 transition-colors ${
                level === l
                  ? "border-lav bg-lav/5"
                  : "border-hairline bg-surface-1 hover:bg-surface-2"
              }`}
            >
              <p className="text-[13px] font-semibold text-ink">{EXPERIENCE_LABEL[l]}</p>
              <p className="text-[11px] text-ink-subtle mt-0.5">
                {l === "first_time" && "I have never competed in a debate round"}
                {l === "novice" && "I am in my first year or tournament season"}
                {l === "jv" && "I have competed for 1-2 years"}
                {l === "varsity" && "I have 3+ years of competitive experience"}
              </p>
            </button>
          ))}
          <Button onClick={() => setStep("ratings")} disabled={!level} className="w-full">
            Continue <ChevronRight size={14} className="ml-1" />
          </Button>
        </div>
      )}

      {/* Step: Self-ratings */}
      {step === "ratings" && (
        <div className="space-y-4">
          <p className="text-[14px] font-semibold text-ink">Rate yourself honestly (1 = needs work, 5 = strong):</p>
          {RATED_SKILLS.map((skill) => (
            <div key={skill.id}>
              <p className="text-[12px] font-medium text-ink mb-1.5">{skill.label}</p>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setRatings((r) => ({ ...r, [skill.id]: n }))}
                    className={`w-9 h-9 rounded-lg border text-[13px] font-semibold transition-colors ${
                      ratings[skill.id] === n
                        ? "border-lav bg-lav text-white"
                        : "border-hairline bg-surface-1 text-ink-subtle hover:bg-surface-2"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setStep("experience")} className="flex-1">
              Back
            </Button>
            <Button onClick={() => setStep("confirm")} className="flex-1">
              Continue <ChevronRight size={14} className="ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Step: Confirm */}
      {step === "confirm" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-lav/20 bg-lav/5 px-4 py-4 space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-lav" aria-hidden />
              <p className="text-[13px] font-semibold text-ink">Ready to build your training plan</p>
            </div>
            <p className="text-[12px] text-ink-subtle">
              Level: <strong>{level ? EXPERIENCE_LABEL[level] : ""}</strong>
            </p>
            <p className="text-[12px] text-ink-subtle">
              {Object.keys(ratings).length} skill ratings recorded
            </p>
            <p className="text-[11px] text-ink-subtle/70">
              Your plan adapts as you practice. These ratings are a starting point, not a grade.
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setStep("ratings")} className="flex-1">
              Back
            </Button>
            <Button onClick={handleSubmit} disabled={loading} className="flex-1">
              {loading ? "Building plan…" : "Start Training →"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
