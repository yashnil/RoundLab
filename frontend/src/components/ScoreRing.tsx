import { motion } from "motion/react";

interface ScoreRingProps {
  score: number;
  max?: number;
  size?: "sm" | "md" | "lg" | "xl";
  label?: string;
  showLabel?: boolean;
}

/**
 * ScoreRing — Circular score display with animation
 * Usage: <ScoreRing score={78} label="Overall" />
 */
export default function ScoreRing({
  score,
  max = 100,
  size = "lg",
  label,
  showLabel = true,
}: ScoreRingProps) {
  const percentage = (score / max) * 100;
  const circumference = 2 * Math.PI * 45; // radius = 45
  const offset = circumference - (percentage / 100) * circumference;

  const sizes = {
    sm: { container: "h-16 w-16", text: "text-lg", label: "text-[10px]", stroke: 6 },
    md: { container: "h-20 w-20", text: "text-xl", label: "text-xs", stroke: 6 },
    lg: { container: "h-28 w-28", text: "text-3xl", label: "text-sm", stroke: 7 },
    xl: { container: "h-36 w-36", text: "text-4xl", label: "text-base", stroke: 8 },
  };

  const sizeConfig = sizes[size];

  // Color based on score
  const getColor = (score: number) => {
    if (score >= 80) return "stroke-ok";
    if (score >= 60) return "stroke-lav";
    if (score >= 40) return "stroke-warn";
    return "stroke-danger";
  };

  return (
    <div className={`relative flex items-center justify-center ${sizeConfig.container}`}>
      {/* Background circle */}
      <svg className="absolute inset-0 -rotate-90 transform">
        <circle
          cx="50%"
          cy="50%"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth={sizeConfig.stroke}
          className="text-hairline"
        />
        {/* Animated progress circle */}
        <motion.circle
          cx="50%"
          cy="50%"
          r="45"
          fill="none"
          stroke="currentColor"
          strokeWidth={sizeConfig.stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
          className={getColor(score)}
        />
      </svg>

      {/* Score text */}
      <div className="flex flex-col items-center">
        <motion.span
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className={`font-bold leading-none text-ink ${sizeConfig.text}`}
        >
          {score}
        </motion.span>
        {showLabel && (
          <span className={`mt-0.5 leading-none text-ink-faint ${sizeConfig.label}`}>
            {label || `/${max}`}
          </span>
        )}
      </div>
    </div>
  );
}
