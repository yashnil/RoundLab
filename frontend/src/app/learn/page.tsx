"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { User, Users, Plus, Trophy } from "lucide-react";
import PageShell from "@/components/PageShell";
import ActionCard from "@/components/ActionCard";
import SectionHeader from "@/components/SectionHeader";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild } from "@/lib/motion";
import type { ProgressSummary, UserTeam } from "@/types";

export default function LearnPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [teamCount, setTeamCount] = useState<number>(0);

  useEffect(() => {
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) {
          router.replace("/login");
          return;
        }

        setUserId(data.user.id);

        // Fetch progress and teams in parallel
        try {
          const [progressData, userTeams] = await Promise.all([
            apiFetch<ProgressSummary>(`/users/${data.user.id}/progress`),
            apiFetch<UserTeam[]>(`/teams/users/${data.user.id}`),
          ]);

          setProgress(progressData);
          setTeamCount(userTeams.length);
        } catch (err) {
          console.error("Failed to fetch user data:", err);
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
    <PageShell maxWidth="5xl">
      <div className="flex flex-col gap-8 py-12">
        {/* Header */}
        <div className="text-center">
          <SectionHeader
            title="Choose how you want to practice"
            description="Work on your own with AI coaching, or join a team to practice together."
          />
        </div>

        {/* Two-card layout */}
        <motion.div
          className="grid grid-cols-1 gap-6 lg:grid-cols-2"
          variants={staggerParent(0.1)}
          initial="hidden"
          animate="show"
        >
          {/* Individual Practice Card */}
          <motion.div variants={staggerChild}>
            <ActionCard
              title="Individual Practice"
              description="Work on your own speeches, get AI judge feedback, complete drills, and track your progress over time."
              icon={User}
              stats={
                progress
                  ? [
                      { label: "Speeches", value: progress.speech_count },
                      { label: "Feedback", value: progress.feedback_ready_count },
                      { label: "Drills", value: progress.drills_assigned_count },
                    ]
                  : undefined
              }
              primaryAction={{
                label: "View Dashboard",
                href: "/dashboard",
              }}
              secondaryAction={{
                label: "New Speech",
                href: "/session",
              }}
              variant="featured"
            />
          </motion.div>

          {/* Team Practice Card */}
          <motion.div variants={staggerChild}>
            <ActionCard
              title="Team Practice"
              description="Join a team, share invite codes, and let coaches track practice activity across all members."
              icon={Users}
              stats={
                teamCount > 0
                  ? [{ label: "Teams", value: teamCount }]
                  : undefined
              }
              primaryAction={{
                label: teamCount > 0 ? "View Teams" : "Join or Create Team",
                href: "/team",
              }}
              badge={teamCount === 0 ? "Optional" : undefined}
            />
          </motion.div>
        </motion.div>

        {/* Bottom note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center text-xs text-ink-faint"
        >
          Not sure which to choose? Start with Individual Practice to build foundational skills.
        </motion.p>
      </div>
    </PageShell>
  );
}
