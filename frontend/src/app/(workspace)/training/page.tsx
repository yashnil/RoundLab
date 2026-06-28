"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase";
import {
  fetchMasteryProfile,
  fetchActivePlan,
  fetchDiagnostic,
  generatePlan,
} from "@/lib/trainingApi";
import { TrainingPlanCard } from "@/components/training/TrainingPlanCard";
import { MasteryExplanation } from "@/components/training/MasteryExplanation";
import { SkillMasteryRing } from "@/components/training/SkillMasteryRing";
import type { MasteryProfile, TrainingPlan, DiagnosticData, MasteryState, MasteryScore } from "@/types/training";
import { MASTERY_STATE_COLOR, MASTERY_STATE_LABEL } from "@/types/training";
import { TrendingUp, BookOpen, Target, Star } from "lucide-react";
import { apiFetch } from "@/lib/api";

// Skill names from the backend (abbreviated for display)
const SKILL_NAME_MAP: Record<string, string> = {
  warranting: "Warranting",
  weighing: "Weighing",
  extensions: "Extensions",
  responses: "Responses",
  clash: "Clash",
  evidence_use: "Evidence Use",
  judge_adaptation: "Judge Adaptation",
  clarity: "Clarity",
  organization: "Organization",
  pacing: "Pacing",
  emphasis: "Emphasis",
  confidence: "Confidence",
  concision: "Concision",
  audience_adaptation: "Audience Adaptation",
  evidence_explanation: "Evidence Explanation",
  claim_construction: "Claim Construction",
  impact_explanation: "Impact Explanation",
  citation_quality: "Citation Quality",
  frontlining: "Frontlining",
  collapse: "Collapse",
  comparative_analysis: "Comparative Analysis",
  crossfire_questioning: "Crossfire Questioning",
  crossfire_answering: "Crossfire Answering",
  constructive_skill: "Constructive",
  rebuttal_skill: "Rebuttal",
  summary_skill: "Summary",
  final_focus_skill: "Final Focus",
  crossfire_skill: "Crossfire",
};

function SkillRow({ skillId, mastery }: { skillId: string; mastery: MasteryScore }) {
  const name = SKILL_NAME_MAP[skillId] ?? skillId;
  const color = MASTERY_STATE_COLOR[mastery.mastery_state as MasteryState];
  const label = MASTERY_STATE_LABEL[mastery.mastery_state as MasteryState];
  return (
    <div className="flex items-center gap-3 py-2 border-b border-hairline last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-medium text-ink">{name}</p>
        <p className={`text-[10px] ${color}`}>{label}</p>
      </div>
      <div className="shrink-0 w-28 bg-surface-3 rounded-full h-1.5">
        <div
          className="h-full rounded-full bg-lav transition-all"
          style={{ width: `${mastery.mastery_score}%` }}
        />
      </div>
      <span className="text-[11px] text-ink-subtle tabular-nums w-8 text-right">
        {mastery.mastery_score.toFixed(0)}
      </span>
    </div>
  );
}

export default function TrainingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [masteryProfile, setMasteryProfile] = useState<MasteryProfile | null>(null);
  const [plan, setPlan] = useState<TrainingPlan | null>(null);
  const [diagnostic, setDiagnostic] = useState<DiagnosticData | null>(null);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [activeTab, setActiveTab] = useState<"plan" | "mastery">("plan");

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) {
          router.replace("/login?next=/training");
          return;
        }
        const [profile, activePlan, diag] = await Promise.all([
          fetchMasteryProfile().catch(() => null),
          fetchActivePlan().catch(() => null),
          fetchDiagnostic().catch(() => null),
        ]);
        setMasteryProfile(profile);
        setPlan(activePlan);
        setDiagnostic(diag);
      })
      .catch(() => setErr("Could not load training data."))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleGeneratePlan() {
    setGeneratingPlan(true);
    try {
      const newPlan = await generatePlan({ plan_type: "4_week" });
      setPlan(newPlan);
    } catch {
      setErr("Failed to generate plan.");
    } finally {
      setGeneratingPlan(false);
    }
  }

  async function handleNextWeek() {
    if (!plan) return;
    setAdvancing(true);
    try {
      await apiFetch(`/training/plans/${plan.id}/week`, {
        method: "PUT",
        body: JSON.stringify({ current_week: plan.current_week + 1 }),
      });
      setPlan((p) => (p ? { ...p, current_week: p.current_week + 1 } : p));
    } catch {
      setErr("Could not advance week.");
    } finally {
      setAdvancing(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </div>
    );
  }

  if (err) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <p className="text-danger text-[13px]">{err}</p>
      </div>
    );
  }

  // Prompt diagnostic if not done
  if (!diagnostic || diagnostic.status !== "completed") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-ink">Training Plan</h1>
          <p className="text-[13px] text-ink-subtle mt-1">
            Dissio builds a personalized plan based on your skill level.
          </p>
        </div>
        <div className="rounded-2xl border border-lav/20 bg-lav/5 px-6 py-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-lav/10 flex items-center justify-center mx-auto">
            <Target size={22} className="text-lav" aria-hidden />
          </div>
          <div>
            <p className="text-[15px] font-bold text-ink">Start with a quick diagnostic</p>
            <p className="text-[13px] text-ink-subtle mt-1">
              Takes 5 minutes. Tells Dissio where to start your training.
            </p>
          </div>
          <Link href="/diagnostic">
            <Button className="px-6">Begin Diagnostic</Button>
          </Link>
        </div>

        {/* Or skip and generate a default plan */}
        <div className="text-center">
          <button
            onClick={handleGeneratePlan}
            disabled={generatingPlan}
            className="text-[12px] text-ink-subtle hover:text-ink underline-offset-2 hover:underline"
          >
            {generatingPlan ? "Generating…" : "Skip diagnostic — generate a default 4-week plan"}
          </button>
        </div>
      </div>
    );
  }

  // Sort skills by mastery score descending for display
  const sortedSkills = masteryProfile
    ? Object.entries(masteryProfile.skills)
        .filter(([, m]) => m.mastery_state !== "not_started")
        .sort(([, a], [, b]) => b.mastery_score - a.mastery_score)
    : [];

  const topStrengths = sortedSkills.slice(0, 3);
  const topPriorities = sortedSkills
    .filter(([, m]) => m.mastery_score < 50)
    .slice(-3)
    .reverse();

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-ink">Training Plan</h1>
          <p className="text-[13px] text-ink-subtle mt-0.5">Public Forum · Novice track</p>
        </div>
        {!plan && (
          <Button size="sm" onClick={handleGeneratePlan} disabled={generatingPlan}>
            {generatingPlan ? "Building…" : "Generate Plan"}
          </Button>
        )}
      </div>

      {/* Quick stats */}
      {masteryProfile && (
        <div className="grid grid-cols-3 gap-3">
          {[
            {
              label: "Mastered",
              value: Object.values(masteryProfile.skills).filter(
                (m) => m.mastery_state === "mastered"
              ).length,
              icon: <Star size={14} className="text-lav" />,
            },
            {
              label: "In Progress",
              value: Object.values(masteryProfile.skills).filter((m) =>
                ["developing", "introduced"].includes(m.mastery_state)
              ).length,
              icon: <TrendingUp size={14} className="text-ok" />,
            },
            {
              label: "To Refresh",
              value: Object.values(masteryProfile.skills).filter(
                (m) => m.mastery_state === "needs_refresh"
              ).length,
              icon: <BookOpen size={14} className="text-warn" />,
            },
          ].map(({ label, value, icon }) => (
            <div key={label} className="rounded-xl border border-hairline bg-surface-1 px-3 py-3">
              <div className="flex items-center gap-1.5 mb-1">
                {icon}
                <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">{label}</p>
              </div>
              <p className="text-[22px] font-bold text-ink tabular-nums">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-hairline">
        {(["plan", "mastery"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-[13px] font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-lav text-lav"
                : "border-transparent text-ink-subtle hover:text-ink"
            }`}
            aria-selected={activeTab === tab}
          >
            {tab === "plan" ? "Training Plan" : "Skill Mastery"}
          </button>
        ))}
      </div>

      {/* Plan tab */}
      {activeTab === "plan" && (
        <div className="space-y-4">
          {plan ? (
            <TrainingPlanCard plan={plan} onNextWeek={handleNextWeek} advancing={advancing} />
          ) : (
            <div className="rounded-2xl border border-hairline bg-surface-1 px-5 py-8 text-center">
              <p className="text-[13px] text-ink-subtle">No active plan. Generate one above.</p>
            </div>
          )}

          {/* Priority skills */}
          {topPriorities.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
                Priority Skills
              </p>
              {topPriorities.map(([skillId, mastery]) => (
                <MasteryExplanation
                  key={skillId}
                  mastery={mastery}
                  skillName={SKILL_NAME_MAP[skillId] ?? skillId}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Mastery tab */}
      {activeTab === "mastery" && masteryProfile && (
        <div className="space-y-4">
          {/* Strengths */}
          {topStrengths.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-ok">Strengths</p>
              <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-1 divide-y divide-hairline">
                {topStrengths.map(([id, m]) => (
                  <SkillRow key={id} skillId={id} mastery={m} />
                ))}
              </div>
            </div>
          )}

          {/* All skills */}
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">All Skills</p>
            <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-1 divide-y divide-hairline">
              {Object.entries(masteryProfile.skills)
                .filter(([, m]) => m.evidence_count > 0)
                .sort(([, a], [, b]) => b.mastery_score - a.mastery_score)
                .map(([id, m]) => (
                  <SkillRow key={id} skillId={id} mastery={m} />
                ))}
            </div>
          </div>

          {/* SkillMasteryRing: hidden rings for the top skills (accessible detail) */}
          {topStrengths.length > 0 && (
            <div className="flex gap-4 flex-wrap">
              {topStrengths.map(([id, m]) => (
                <div key={id} className="flex flex-col items-center gap-1">
                  <SkillMasteryRing mastery={m} size="sm" showLabel={false} />
                  <span className="text-[10px] text-ink-subtle">{SKILL_NAME_MAP[id] ?? id}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
