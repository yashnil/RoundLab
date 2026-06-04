"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { User, Users, ArrowRight, Plus, Trophy } from "lucide-react";
import AppNav from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { createClient } from "@/lib/supabase";
import { fadeUp, staggerParent, staggerChild } from "@/lib/motion";

export default function LearnPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    createClient().auth.getUser()
      .then(({ data }) => {
        if (!data.user) {
          router.replace("/login");
        } else {
          setUserId(data.user.id);
        }
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-hairline border-t-lav" />
      </div>
    );
  }

  if (!userId) return null;

  return (
    <div className="min-h-screen bg-canvas">
      <AppNav />

      <div className="mx-auto max-w-5xl px-6 py-16">
        {/* Header */}
        <motion.div {...fadeUp(0)} className="mb-12 flex flex-col gap-3 text-center">
          <h1 className="text-display text-ink">Choose how you want to practice</h1>
          <p className="mx-auto max-w-lg text-base leading-relaxed text-ink-subtle">
            Work on your own with AI coaching, or join a team to practice together.
          </p>
        </motion.div>

        {/* Two-card layout */}
        <motion.div
          className="grid grid-cols-1 gap-6 lg:grid-cols-2"
          variants={staggerParent(0.1)}
          initial="hidden"
          animate="show"
        >
          {/* Individual Practice Card */}
          <motion.div variants={staggerChild}>
            <Card className="group h-full transition-all duration-200 hover:border-lav/40 hover:shadow-lg hover:shadow-lav/5">
              <CardContent className="flex h-full flex-col gap-6 p-8">
                {/* Icon */}
                <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-lav/20 bg-lav/10 transition-all duration-200 group-hover:border-lav/40 group-hover:bg-lav/20">
                  <User size={24} className="text-lav" />
                </div>

                {/* Content */}
                <div className="flex flex-1 flex-col gap-3">
                  <h2 className="text-headline text-ink">Individual Practice</h2>
                  <p className="text-sm leading-relaxed text-ink-subtle">
                    Work on your own speeches, get AI judge feedback, complete drills, and track your progress over time.
                  </p>

                  {/* Features */}
                  <ul className="mt-2 flex flex-col gap-2">
                    {[
                      "AI flow analysis",
                      "Judge-style feedback",
                      "Personalized drills",
                      "Progress tracking",
                    ].map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-xs text-ink-muted">
                        <span className="h-1 w-1 shrink-0 rounded-full bg-lav" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2">
                  <Button asChild size="default" className="w-full gap-2">
                    <a href="/dashboard">
                      <Trophy size={14} />
                      Continue to Individual Practice
                    </a>
                  </Button>
                  <Button asChild variant="outline" size="default" className="w-full gap-2">
                    <a href="/session">
                      <Plus size={14} />
                      Start New Speech
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Team Practice Card */}
          <motion.div variants={staggerChild}>
            <Card className="group h-full transition-all duration-200 hover:border-indigo/40 hover:shadow-lg hover:shadow-indigo/5">
              <CardContent className="flex h-full flex-col gap-6 p-8">
                {/* Icon */}
                <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-indigo/20 bg-indigo/10 transition-all duration-200 group-hover:border-indigo/40 group-hover:bg-indigo/20">
                  <Users size={24} className="text-indigo" />
                </div>

                {/* Content */}
                <div className="flex flex-1 flex-col gap-3">
                  <h2 className="text-headline text-ink">Team Practice</h2>
                  <p className="text-sm leading-relaxed text-ink-subtle">
                    Join a team, share invite codes, and let coaches track practice activity across all members.
                  </p>

                  {/* Features */}
                  <ul className="mt-2 flex flex-col gap-2">
                    {[
                      "Create or join teams",
                      "Share practice progress",
                      "Coach dashboard",
                      "Team leaderboards",
                    ].map((feature) => (
                      <li key={feature} className="flex items-center gap-2 text-xs text-ink-muted">
                        <span className="h-1 w-1 shrink-0 rounded-full bg-indigo" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2">
                  <Button asChild size="default" variant="outline" className="w-full gap-2 border-indigo/20 bg-indigo/5 text-indigo hover:border-indigo/40 hover:bg-indigo/10 hover:text-indigo">
                    <a href="/team">
                      <ArrowRight size={14} />
                      Go to Team Practice
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>

        {/* Bottom note */}
        <motion.p
          {...fadeUp(0.3)}
          className="mt-8 text-center text-xs text-ink-faint"
        >
          Not sure which to choose? Start with Individual Practice to build foundational skills.
        </motion.p>
      </div>
    </div>
  );
}
