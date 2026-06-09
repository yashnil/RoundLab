"use client";

import { motion } from "motion/react";
import { Eye, GitBranch, BarChart3, BookOpen } from "lucide-react";
import { T } from "@/lib/motion";

export type JudgeViewMode = "coach" | "lay" | "flow" | "tech";

interface JudgeModeConfig {
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  helper: string;
  emphasis: string[];
}

const MODES: Record<JudgeViewMode, JudgeModeConfig> = {
  coach: {
    label: "Coach",
    icon: BookOpen,
    helper: "Fix actions and drill targets",
    emphasis: ["strengths", "weaknesses", "drills"],
  },
  lay: {
    label: "Lay",
    icon: Eye,
    helper: "Clarity, delivery, and persuasion",
    emphasis: ["clarity", "real-world", "persuasion"],
  },
  flow: {
    label: "Flow",
    icon: GitBranch,
    helper: "Drops, extensions, and argument depth",
    emphasis: ["extensions", "drops", "weighing"],
  },
  tech: {
    label: "Tech",
    icon: BarChart3,
    helper: "Evidence quality, warrants, and weighing",
    emphasis: ["conceded", "line-by-line", "judge-adaptation"],
  },
};

interface JudgeModeSelectorProps {
  value: JudgeViewMode;
  onChange: (mode: JudgeViewMode) => void;
}

export default function JudgeModeSelector({ value, onChange }: JudgeModeSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="section-stamp">Judge Lens</span>
      <div className="flex gap-1 rounded-lg border border-hairline bg-surface-2 p-1">
        {(Object.entries(MODES) as [JudgeViewMode, JudgeModeConfig][]).map(([key, config]) => {
          const Icon = config.icon;
          const isActive = value === key;

          return (
            <motion.button
              key={key}
              type="button"
              onClick={() => onChange(key)}
              whileTap={{ scale: 0.97 }}
              transition={T.fast}
              className={[
                "relative flex flex-1 flex-col items-center gap-1 rounded-md px-2 py-2 text-center transition-colors",
                isActive
                  ? "bg-lav text-white"
                  : "text-ink-subtle hover:bg-surface-3 hover:text-ink",
              ].join(" ")}
              title={config.helper}
            >
              <Icon size={12} className={isActive ? "text-white" : "text-ink-faint"} />
              <span className="text-[10px] font-semibold leading-none">{config.label}</span>
            </motion.button>
          );
        })}
      </div>
      {/* Helper text for active mode */}
      <p className="text-xs text-ink-faint">{MODES[value].helper}</p>
    </div>
  );
}
