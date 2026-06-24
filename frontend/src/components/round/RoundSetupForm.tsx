"use client";

import { useState } from "react";
import type { RoundSimulationConfig } from "@/types/round";
import { defaultRoundConfig } from "@/lib/roundModel";

interface Props {
  onStart: (config: RoundSimulationConfig) => void;
  loading?: boolean;
}

const JUDGE_TYPES = [
  { value: "flow", label: "Flow Judge" },
  { value: "lay", label: "Lay Judge" },
  { value: "parent", label: "Parent Judge" },
  { value: "technical", label: "Technical Judge" },
  { value: "coach", label: "Coach Judge" },
];

const DIFFICULTY_OPTIONS = [
  { value: "novice", label: "Novice — Simple arguments, coaching hints" },
  { value: "jv", label: "JV — Standard clash, moderate depth" },
  { value: "varsity", label: "Varsity — Line-by-line, evidence indictments" },
];

const FORMAT_OPTIONS = [
  { value: "full", label: "Full Round (all 13 phases)" },
  { value: "shortened", label: "Shortened (no grand/final crossfire)" },
  { value: "speech_stage_drill", label: "Speech Stage Drill" },
  { value: "evidence_testing", label: "Evidence Testing" },
];

export function RoundSetupForm({ onStart, loading }: Props) {
  const [config, setConfig] = useState<RoundSimulationConfig>(defaultRoundConfig());

  function patch(updates: Partial<RoundSimulationConfig>) {
    setConfig((c) => ({ ...c, ...updates }));
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Round Simulation Setup</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your practice round. The AI opponent is constrained to your saved preparation.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Resolution</h2>
        <textarea
          className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[64px] resize-none"
          placeholder="Enter the resolution text..."
          value={config.resolution}
          onChange={(e) => patch({ resolution: e.target.value })}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Round Setup</h2>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs font-medium text-muted-foreground mb-1 block">Format</span>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={config.format}
              onChange={(e) => patch({ format: e.target.value as RoundSimulationConfig["format"] })}
            >
              {FORMAT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-medium text-muted-foreground mb-1 block">Your Side</span>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={config.student_side}
              onChange={(e) => patch({ student_side: e.target.value as "pro" | "con" })}
            >
              <option value="pro">Pro (Affirmative)</option>
              <option value="con">Con (Negative)</option>
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-medium text-muted-foreground mb-1 block">Speaking Order</span>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={config.speaking_order}
              onChange={(e) => patch({ speaking_order: e.target.value as "first" | "second" })}
            >
              <option value="first">Speak First</option>
              <option value="second">Speak Second</option>
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-medium text-muted-foreground mb-1 block">Speaker Role</span>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={config.speaker_role}
              onChange={(e) => patch({ speaker_role: e.target.value as "first" | "second" })}
            >
              <option value="first">First Speaker</option>
              <option value="second">Second Speaker</option>
            </select>
          </label>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Judge & Opponent</h2>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs font-medium text-muted-foreground mb-1 block">Judge Type</span>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={config.judge_type}
              onChange={(e) => patch({ judge_type: e.target.value })}
            >
              {JUDGE_TYPES.map((j) => (
                <option key={j.value} value={j.value}>{j.label}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-medium text-muted-foreground mb-1 block">Opponent Difficulty</span>
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={config.opponent_difficulty}
              onChange={(e) => patch({ opponent_difficulty: e.target.value as RoundSimulationConfig["opponent_difficulty"] })}
            >
              {DIFFICULTY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Options</h2>
        <div className="flex flex-col gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={config.coaching_hints_enabled}
              onChange={(e) => patch({ coaching_hints_enabled: e.target.checked })}
              className="rounded"
            />
            Show coaching hints between speeches
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={config.pauses_allowed}
              onChange={(e) => patch({ pauses_allowed: e.target.checked })}
              className="rounded"
            />
            Allow pausing the round
          </label>
        </div>
      </section>

      <div className="pt-2">
        <p className="text-xs text-muted-foreground mb-4">
          After creating the round, you can load approved evidence cards, blockfiles, and frontlines
          before starting.
        </p>
        <button
          onClick={() => onStart(config)}
          disabled={loading || !config.resolution.trim()}
          className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50 transition-opacity"
        >
          {loading ? "Creating round..." : "Create Round"}
        </button>
      </div>
    </div>
  );
}
