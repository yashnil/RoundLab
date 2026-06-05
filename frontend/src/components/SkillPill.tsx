import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SkillPillProps {
  name: string;
  score: number;
  trend?: "up" | "down" | "same";
  onClick?: () => void;
}

/**
 * SkillPill — Compact skill display with trend
 * Usage: <SkillPill name="Warranting" score={12} trend="up" />
 */
export default function SkillPill({ name, score, trend, onClick }: SkillPillProps) {
  const trendIcons = {
    up: <TrendingUp size={12} className="text-ok" />,
    down: <TrendingDown size={12} className="text-danger" />,
    same: <Minus size={12} className="text-ink-faint" />,
  };

  const scoreColor = (score: number) => {
    if (score >= 16) return "text-ok";
    if (score >= 12) return "text-lav";
    if (score >= 8) return "text-warn";
    return "text-danger";
  };

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-lg border border-hairline bg-surface-1 px-3 py-1.5 transition-colors hover:border-hairline-strong hover:bg-surface-2"
    >
      <span className="text-sm text-ink-subtle">{name}</span>
      <span className={`text-sm font-bold ${scoreColor(score)}`}>{score}</span>
      {trend && trendIcons[trend]}
    </button>
  );
}
