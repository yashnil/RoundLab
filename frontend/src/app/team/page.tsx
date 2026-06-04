"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  Users, Copy, Check, TrendingUp, Mic, Target, Headphones,
  UserPlus, Plus, MessageSquare, ChevronRight,
} from "lucide-react";
import AppNav from "@/components/AppNav";
import EmptyState from "@/components/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild } from "@/lib/motion";
import type { UserTeam, TeamDashboard } from "@/types";

function fmtDate(iso: string | null) {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short", day: "numeric",
  });
}

export default function TeamPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [teams, setTeams] = useState<UserTeam[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<UserTeam | null>(null);
  const [dashboard, setDashboard] = useState<TeamDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // Create team state
  const [creating, setCreating] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [createErr, setCreateErr] = useState("");

  // Join team state
  const [joining, setJoining] = useState(false);
  const [joinCode, setJoinCode] = useState("");
  const [joinErr, setJoinErr] = useState("");

  // Invite code copy
  const [copied, setCopied] = useState(false);
  const [copiedMessage, setCopiedMessage] = useState(false);

  useEffect(() => {
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);

        // Fetch user teams (do NOT auto-select)
        const userTeams = await apiFetch<UserTeam[]>(`/teams/users/${data.user.id}`);
        setTeams(userTeams);
      })
      .catch(() => setErr("Could not load team data. Please refresh or try again."))
      .finally(() => setLoading(false));
  }, [router]);

  // Handle team selection - toggle on/off
  async function selectTeam(team: UserTeam) {
    // If clicking already selected team, deselect it
    if (selectedTeam?.team_id === team.team_id) {
      setSelectedTeam(null);
      setDashboard(null);
      return;
    }

    setSelectedTeam(team);
    setDashboard(null); // Clear previous dashboard

    // Fetch dashboard if coach
    if (team.role === "coach" && userId) {
      try {
        const dash = await apiFetch<TeamDashboard>(
          `/teams/${team.team_id}/dashboard?user_id=${userId}`
        );
        setDashboard(dash);
      } catch {}
    }
  }

  async function handleCreateTeam() {
    if (!userId || !newTeamName.trim()) return;
    setCreateErr("");
    setCreating(true);

    try {
      const team = await apiFetch<{ id: string; name: string; invite_code: string; created_by: string; created_at: string }>(
        "/teams",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: newTeamName.trim(), created_by: userId }),
        }
      );

      // Refresh teams
      const userTeams = await apiFetch<UserTeam[]>(`/teams/users/${userId}`);
      setTeams(userTeams);

      // Auto-select the new team
      const newTeam = userTeams.find((t) => t.team_id === team.id);
      if (newTeam) {
        await selectTeam(newTeam);
      }

      setNewTeamName("");
    } catch (e: unknown) {
      setCreateErr(e instanceof Error ? e.message : "Failed to create team");
    } finally {
      setCreating(false);
    }
  }

  async function handleJoinTeam() {
    if (!userId || !joinCode.trim()) return;
    setJoinErr("");
    setJoining(true);

    try {
      await apiFetch("/teams/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invite_code: joinCode.trim().toUpperCase(), user_id: userId }),
      });

      // Refresh teams
      const userTeams = await apiFetch<UserTeam[]>(`/teams/users/${userId}`);
      setTeams(userTeams);

      // Auto-select the new team
      const newTeam = userTeams.find((t) => t.invite_code === joinCode.trim().toUpperCase());
      if (newTeam) {
        await selectTeam(newTeam);
      }

      setJoinCode("");
    } catch (e: unknown) {
      setJoinErr(e instanceof Error ? e.message : "Failed to join team");
    } finally {
      setJoining(false);
    }
  }

  function copyInviteCode() {
    if (!selectedTeam) return;
    navigator.clipboard.writeText(selectedTeam.invite_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function copyInviteMessage() {
    if (!selectedTeam) return;
    const appUrl = typeof window !== "undefined" ? window.location.origin : "";
    const message = `Join our RoundLab practice team:
1. Go to ${appUrl}
2. Sign in
3. Open Team
4. Enter invite code: ${selectedTeam.invite_code}
5. Record one 45-90 second Summary or Final Focus before our next practice.`;
    navigator.clipboard.writeText(message);
    setCopiedMessage(true);
    setTimeout(() => setCopiedMessage(false), 2000);
  }

  if (loading) {
    return (
      <>
        <AppNav />
        <main className="min-h-screen bg-canvas">
          <div className="mx-auto flex max-w-4xl flex-col gap-5 px-6 py-9">
            <Skeleton className="h-6 w-48 rounded-lg" />
            <Skeleton className="h-4 w-60 rounded-lg" />
            {Array.from({ length: 2 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="py-8">
                  <Skeleton className="h-20 w-full rounded-lg" />
                </CardContent>
              </Card>
            ))}
          </div>
        </main>
      </>
    );
  }

  if (err) {
    return (
      <>
        <AppNav />
        <main className="min-h-screen bg-canvas">
          <div className="mx-auto max-w-4xl px-6 py-16">
            <p className="text-sm text-danger">{err}</p>
          </div>
        </main>
      </>
    );
  }

  // No teams yet - show create/join cards
  if (teams.length === 0) {
    return (
      <>
        <AppNav />
        <main className="min-h-screen bg-canvas">
          <motion.div
            className="mx-auto flex max-w-4xl flex-col gap-7 px-6 py-9"
            variants={staggerParent(0.07, 0.05)}
            initial="hidden"
            animate="show"
          >
            <motion.div variants={staggerChild} className="flex flex-col gap-1">
              <h1 className="text-title text-ink">Team</h1>
              <p className="text-sm text-ink-subtle">
                Create a team to coach students or join a team to practice together.
              </p>
            </motion.div>

            <motion.div variants={staggerChild} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Create Team */}
              <Card>
                <CardContent className="flex flex-col gap-4 px-5 py-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-lav/20 bg-lav/10">
                      <Plus size={18} className="text-lav" />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <p className="text-sm font-semibold text-ink">Create Team</p>
                      <p className="text-xs text-ink-subtle">For coaches and team leaders</p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <Input
                      placeholder="Team name"
                      value={newTeamName}
                      onChange={(e) => setNewTeamName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleCreateTeam();
                      }}
                      disabled={creating}
                    />
                    {createErr && <p className="text-xs text-danger">{createErr}</p>}
                    <Button
                      onClick={handleCreateTeam}
                      disabled={creating || !newTeamName.trim()}
                      size="sm"
                      className="w-full"
                    >
                      {creating ? "Creating…" : "Create Team"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Join Team */}
              <Card>
                <CardContent className="flex flex-col gap-4 px-5 py-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-indigo/20 bg-indigo/10">
                      <UserPlus size={18} className="text-indigo" />
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <p className="text-sm font-semibold text-ink">Join Team</p>
                      <p className="text-xs text-ink-subtle">Enter invite code from your coach</p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <Input
                      placeholder="Invite code"
                      value={joinCode}
                      onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleJoinTeam();
                      }}
                      disabled={joining}
                      className="font-mono uppercase"
                    />
                    {joinErr && <p className="text-xs text-danger">{joinErr}</p>}
                    <Button
                      onClick={handleJoinTeam}
                      disabled={joining || !joinCode.trim()}
                      size="sm"
                      className="w-full"
                      variant="secondary"
                    >
                      {joining ? "Joining…" : "Join Team"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        </main>
      </>
    );
  }

  // Has teams - show team hub
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-canvas">
        <motion.div
          className="mx-auto flex max-w-4xl flex-col gap-5 px-6 py-7"
          variants={staggerParent(0.07, 0.05)}
          initial="hidden"
          animate="show"
        >
          {/* Header */}
          <motion.div variants={staggerChild} className="flex flex-col gap-1">
            <h1 className="text-title text-ink">Your Teams</h1>
            <p className="text-sm text-ink-subtle">
              Manage your teams, track practice activity, and share invite codes with students.
            </p>
          </motion.div>

          {/* Create / Join Actions */}
          <motion.div variants={staggerChild} className="flex flex-wrap gap-2">
            <Button
              onClick={() => {
                const createInput = document.querySelector('input[placeholder="Team name"]') as HTMLInputElement;
                createInput?.focus();
                createInput?.scrollIntoView({ behavior: "smooth", block: "center" });
              }}
              size="sm"
              className="gap-1.5"
            >
              <Plus size={12} />
              Create New Team
            </Button>
            <Button
              onClick={() => {
                const joinInput = document.querySelector('input[placeholder="Invite code"]') as HTMLInputElement;
                joinInput?.focus();
                joinInput?.scrollIntoView({ behavior: "smooth", block: "center" });
              }}
              size="sm"
              variant="secondary"
              className="gap-1.5"
            >
              <UserPlus size={12} />
              Join Team
            </Button>
          </motion.div>

          {/* Team Cards */}
          <motion.div variants={staggerChild} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {teams.map((team) => (
              <Card
                key={team.team_id}
                className={[
                  "cursor-pointer transition-all",
                  selectedTeam?.team_id === team.team_id
                    ? "border-lav/40 bg-lav/5 ring-2 ring-lav/20"
                    : "border-hairline hover:border-hairline-strong",
                ].join(" ")}
                onClick={() => selectTeam(team)}
              >
                <CardContent className="px-5 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 flex-1 items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-lav/20 bg-lav/10">
                        <Users size={18} className="text-lav" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-ink">{team.team_name}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2">
                          <Badge
                            variant={team.role === "coach" ? "indigo" : "default"}
                            className="capitalize"
                          >
                            {team.role}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    {selectedTeam?.team_id === team.team_id && (
                      <Check size={16} className="shrink-0 text-lav" />
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </motion.div>

          {/* Selected Team Details */}
          <AnimatePresence mode="wait">
            {selectedTeam && (
              <motion.div
                key={selectedTeam.team_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
                className="flex flex-col gap-5"
              >

                {/* Invite Code & Actions */}
                <Card className="border-lav/20 bg-lav/5">
                  <CardContent className="px-5 py-4">
                    <div className="mb-3 flex items-center justify-between gap-4">
                      <div>
                        <p className="text-xs font-medium text-lav">Team Invite Code</p>
                        <p className="font-mono text-lg font-bold tracking-wide text-ink">{selectedTeam.invite_code}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button onClick={copyInviteCode} size="sm" variant="secondary" className="gap-1.5">
                        {copied ? <><Check size={12} />Copied</> : <><Copy size={12} />Copy Code</>}
                      </Button>
                      {selectedTeam.role === "coach" && (
                        <Button onClick={copyInviteMessage} size="sm" className="gap-1.5">
                          {copiedMessage ? <><Check size={12} />Copied</> : <><MessageSquare size={12} />Copy Invite Message</>}
                        </Button>
                      )}
                    </div>
                    {selectedTeam.role === "coach" && (
                      <p className="mt-3 text-xs text-ink-faint">
                        Share the invite code or full message with your students.
                      </p>
                    )}
                  </CardContent>
                </Card>

          {/* Coach Dashboard */}
          {selectedTeam?.role === "coach" && dashboard && (
            <>
              {/* Stats */}
              <motion.div variants={staggerChild} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Card>
                  <CardContent className="flex items-center gap-3 px-4 py-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-lav/20 bg-lav/10">
                      <Users size={14} className="text-lav" />
                    </div>
                    <div className="flex flex-col">
                      <p className="text-xl font-bold text-ink">{dashboard.member_count}</p>
                      <p className="text-xs text-ink-subtle">Members</p>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="flex items-center gap-3 px-4 py-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-ok/20 bg-ok/10">
                      <TrendingUp size={14} className="text-ok" />
                    </div>
                    <div className="flex flex-col">
                      <p className="text-xl font-bold text-ink">
                        {dashboard.students.reduce((sum, s) => sum + s.speech_count, 0)}
                      </p>
                      <p className="text-xs text-ink-subtle">Speeches</p>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="flex items-center gap-3 px-4 py-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-indigo/20 bg-indigo/10">
                      <Target size={14} className="text-indigo" />
                    </div>
                    <div className="flex flex-col">
                      <p className="text-xl font-bold text-ink">
                        {dashboard.students.reduce((sum, s) => sum + s.drills_assigned_count, 0)}
                      </p>
                      <p className="text-xs text-ink-subtle">Drills</p>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="flex items-center gap-3 px-4 py-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-amber/20 bg-amber/10">
                      <Headphones size={14} className="text-amber" />
                    </div>
                    <div className="flex flex-col">
                      <p className="text-xl font-bold text-ink">
                        {dashboard.students.reduce((sum, s) => sum + s.drill_attempts_count, 0)}
                      </p>
                      <p className="text-xs text-ink-subtle">Attempts</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Student Progress */}
              <motion.div variants={staggerChild} className="flex flex-col gap-3">
                <p className="text-eyebrow text-ink-subtle">Student Progress</p>
                {dashboard.students.length === 0 ? (
                  <EmptyState
                    Icon={Users}
                    title="No students yet"
                    description="Share your invite code to get students started."
                  />
                ) : (
                  <div className="flex flex-col gap-2">
                    {dashboard.students.map((student) => (
                      <Card key={student.user_id}>
                        <CardContent className="flex items-center gap-4 px-5 py-4">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full border border-hairline bg-surface-2">
                            <span className="text-xs font-semibold text-ink-subtle">
                              {(student.display_name || student.user_id).charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                            <p className="truncate text-sm font-semibold text-ink">
                              {student.display_name || `Student ${student.user_id.slice(0, 8)}`}
                            </p>
                            <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-ink-subtle">
                              <span className="flex items-center gap-1">
                                <Mic size={10} />
                                {student.speech_count} speech{student.speech_count !== 1 ? "es" : ""}
                              </span>
                              <span className="flex items-center gap-1">
                                <Target size={10} />
                                {student.drills_assigned_count} drills
                              </span>
                              <span className="flex items-center gap-1">
                                <Headphones size={10} />
                                {student.drill_attempts_count} attempts
                              </span>
                              <span className="text-ink-faint">Last: {fmtDate(student.latest_practice_at)}</span>
                            </div>
                          </div>
                          {student.feedback_ready_count > 0 && (
                            <Badge variant="green">{student.feedback_ready_count} feedback</Badge>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </motion.div>
            </>
          )}

          {/* Student View */}
          {selectedTeam?.role === "student" && (
            <motion.div variants={staggerChild}>
              <Card>
                <CardContent className="flex flex-col items-center gap-4 px-5 py-8">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full border border-lav/20 bg-lav/10">
                    <Users size={20} className="text-lav" />
                  </div>
                  <div className="flex flex-col items-center gap-1 text-center">
                    <p className="text-sm font-semibold text-ink">You're a student in {selectedTeam.team_name}</p>
                    <p className="text-xs text-ink-subtle">Continue practicing individually</p>
                  </div>
                  <Button asChild size="sm">
                    <a href="/dashboard">Continue Practicing</a>
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}

              </motion.div>
              )}
            </AnimatePresence>

          {/* Create/Join Additional Teams */}
          <motion.div variants={staggerChild} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Create Another Team */}
            <Card id="create-team-section">
              <CardContent className="flex flex-col gap-4 px-5 py-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-lav/20 bg-lav/10">
                    <Plus size={18} className="text-lav" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-semibold text-ink">Create Another Team</p>
                    <p className="text-xs text-ink-subtle">Coach multiple teams</p>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <Input
                    placeholder="Team name"
                    value={newTeamName}
                    onChange={(e) => setNewTeamName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCreateTeam();
                    }}
                    disabled={creating}
                  />
                  {createErr && <p className="text-xs text-danger">{createErr}</p>}
                  <Button
                    onClick={handleCreateTeam}
                    disabled={creating || !newTeamName.trim()}
                    size="sm"
                    className="w-full"
                  >
                    {creating ? "Creating…" : "Create Team"}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Join Another Team */}
            <Card id="join-team-section">
              <CardContent className="flex flex-col gap-4 px-5 py-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-indigo/20 bg-indigo/10">
                    <UserPlus size={18} className="text-indigo" />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-semibold text-ink">Join Another Team</p>
                    <p className="text-xs text-ink-subtle">Get another invite code</p>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <Input
                    placeholder="Invite code"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleJoinTeam();
                    }}
                    disabled={joining}
                    className="font-mono uppercase"
                  />
                  {joinErr && <p className="text-xs text-danger">{joinErr}</p>}
                  <Button
                    onClick={handleJoinTeam}
                    disabled={joining || !joinCode.trim()}
                    size="sm"
                    className="w-full"
                    variant="secondary"
                  >
                    {joining ? "Joining…" : "Join Team"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Team Management Note */}
          <motion.div variants={staggerChild}>
            <Card className="border-hairline/50">
              <CardContent className="px-5 py-3">
                <p className="text-xs text-ink-faint">
                  <span className="font-medium text-ink-subtle">Need to leave a team?</span> Ask your coach for now. Advanced team management is coming soon.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </main>
    </>
  );
}
