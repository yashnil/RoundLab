"use client";

import * as React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.ComponentProps<"div"> {
  value: number;
  max?: number;
  colorClass?: string;
  /** Animate width from 0 on mount */
  animated?: boolean;
  animationDelay?: number;
}

function Progress({
  value,
  max = 100,
  colorClass = "bg-lav",
  animated = false,
  animationDelay = 0,
  className,
  ...props
}: ProgressProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div
      role="progressbar"
      aria-valuenow={value}
      aria-valuemax={max}
      className={cn("h-1 w-full overflow-hidden rounded-full bg-hairline", className)}
      {...props}
    >
      {animated ? (
        <motion.div
          className={cn("h-full rounded-full", colorClass)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, delay: animationDelay, ease: [0.22, 1, 0.36, 1] }}
        />
      ) : (
        <div
          className={cn("h-full rounded-full transition-all duration-500", colorClass)}
          style={{ width: `${pct}%` }}
        />
      )}
    </div>
  );
}

export { Progress };
