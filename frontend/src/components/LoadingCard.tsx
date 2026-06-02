"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { EASE } from "@/lib/motion";

interface LoadingCardProps {
  messages: string[];
  title?: string;
}

export default function LoadingCard({ messages, title }: LoadingCardProps) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % messages.length), 2200);
    return () => clearInterval(t);
  }, [messages.length]);

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-5 py-10">
        {/* Spinner + soft pulse ring */}
        <div className="relative flex items-center justify-center">
          <motion.div
            className="absolute h-9 w-9 rounded-full border border-lav/25"
            animate={{ scale: [1, 1.7, 1], opacity: [0.4, 0, 0.4] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: "easeOut" }}
          />
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-lav">
            <Loader2 size={14} className="animate-spin text-white" />
          </div>
        </div>

        {/* Title */}
        {title && <p className="text-eyebrow text-ink-subtle">{title}</p>}

        {/* Cycling message */}
        <div className="h-5 flex items-center">
          <AnimatePresence mode="wait">
            <motion.p
              key={idx}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2, ease: EASE }}
              className="text-sm text-ink-subtle"
            >
              {messages[idx]}
            </motion.p>
          </AnimatePresence>
        </div>

        {/* Progress track */}
        <div className="flex w-28 items-center gap-1">
          {messages.map((_, i) => (
            <motion.div
              key={i}
              animate={{
                width: i === idx ? 16 : 4,
                opacity: i === idx ? 1 : 0.3,
                backgroundColor: i < idx
                  ? "oklch(0.510 0.156 278)"
                  : i === idx
                  ? "oklch(0.510 0.156 278)"
                  : "oklch(0.270 0.006 264)",
              }}
              transition={{ duration: 0.3, ease: EASE }}
              className="h-1 flex-shrink-0 rounded-full"
            />
          ))}
        </div>

        {/* Step progress text */}
        <p className="text-xs text-ink-faint">
          Step {idx + 1} of {messages.length}
        </p>
      </CardContent>
    </Card>
  );
}
