"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Check, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { EASE } from "@/lib/motion";

interface LoadingCardProps {
  messages: string[];
  title?: string;
  subtitle?: string;
}

export default function LoadingCard({ messages, title, subtitle }: LoadingCardProps) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => Math.min(i + 1, messages.length - 1)), 2400);
    return () => clearInterval(t);
  }, [messages.length]);

  return (
    <Card className="beam-top overflow-hidden">
      <CardContent className="px-6 py-8">
        <div className="flex flex-col gap-6">
          {/* Spinner + title row */}
          <div className="flex items-center gap-4">
            <div className="relative flex shrink-0 items-center justify-center">
              <motion.div
                className="absolute h-12 w-12 rounded-full border border-lav/30"
                animate={{ scale: [1, 1.6, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2.0, repeat: Infinity, ease: "easeOut" }}
              />
              <div className="relative flex h-9 w-9 items-center justify-center rounded-full bg-lav">
                <Loader2 size={16} className="animate-spin text-white" />
              </div>
            </div>
            <div className="flex flex-col gap-0.5">
              {title && (
                <p className="text-sm font-semibold text-ink">{title}</p>
              )}
              {subtitle && (
                <p className="text-xs text-ink-faint">{subtitle}</p>
              )}
              {!title && (
                <p className="text-sm font-semibold text-ink">Analyzing your speech</p>
              )}
              {!subtitle && (
                <p className="text-xs text-ink-faint">This takes 30–90 seconds</p>
              )}
            </div>
          </div>

          {/* Step list — debate-specific pipeline */}
          <div className="flex flex-col gap-1">
            {messages.map((msg, i) => {
              const isDone    = i < idx;
              const isActive  = i === idx;
              const isPending = i > idx;

              return (
                <motion.div
                  key={i}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors"
                  animate={{
                    backgroundColor: isActive
                      ? "oklch(0.510 0.156 278 / 0.07)"
                      : "transparent",
                  }}
                  transition={{ duration: 0.3, ease: EASE }}
                >
                  {/* Step indicator */}
                  <div className="flex h-5 w-5 shrink-0 items-center justify-center">
                    {isDone ? (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        className="flex h-5 w-5 items-center justify-center rounded-full bg-lav"
                      >
                        <Check size={10} strokeWidth={2.5} className="text-white" />
                      </motion.div>
                    ) : isActive ? (
                      <div className="h-2 w-2 rounded-full bg-lav analysis-step-active" />
                    ) : (
                      <div className="h-1.5 w-1.5 rounded-full bg-hairline-strong" />
                    )}
                  </div>

                  {/* Message */}
                  <AnimatePresence mode="wait">
                    <p
                      className={[
                        "text-sm transition-colors",
                        isDone    ? "text-ink-faint line-through"   : "",
                        isActive  ? "font-medium text-ink"          : "",
                        isPending ? "text-ink-faint"                : "",
                      ].join(" ")}
                    >
                      {msg}
                    </p>
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>

          {/* Step counter */}
          <p className="text-center text-xs text-ink-faint">
            Step {Math.min(idx + 1, messages.length)} of {messages.length}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
