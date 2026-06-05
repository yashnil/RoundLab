import { type LucideIcon } from "lucide-react";
import { motion } from "motion/react";

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string;
  changeType?: "positive" | "negative" | "neutral";
  icon?: LucideIcon;
  color?: "lav" | "ok" | "warn" | "danger";
}

/**
 * MetricCard — Dashboard stat display
 * Usage: <MetricCard label="XP" value={1250} change="+50 this week" />
 */
export default function MetricCard({
  label,
  value,
  change,
  changeType = "neutral",
  icon: Icon,
  color = "lav",
}: MetricCardProps) {
  const colorClasses = {
    lav: "bg-lav/10 text-lav",
    ok: "bg-ok/10 text-ok",
    warn: "bg-warn/10 text-warn",
    danger: "bg-danger/10 text-danger",
  };

  const changeColors = {
    positive: "text-ok",
    negative: "text-danger",
    neutral: "text-ink-subtle",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-hairline bg-surface-1 p-4 transition-colors hover:border-hairline-strong"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider">{label}</p>
          <p className="mt-1 text-2xl font-bold text-ink tracking-tight">{value}</p>
          {change && (
            <p className={`mt-1 text-xs ${changeColors[changeType]}`}>{change}</p>
          )}
        </div>
        {Icon && (
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${colorClasses[color]}`}>
            <Icon size={16} />
          </div>
        )}
      </div>
    </motion.div>
  );
}
