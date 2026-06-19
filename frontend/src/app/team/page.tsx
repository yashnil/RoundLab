"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  Users, Copy, Check, Mic, Target, Headphones,
  UserPlus, Plus, MessageSquare, ChevronRight, ClipboardList, Inbox, ArrowRight, AlertTriangle,
} from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import EmptyState from "@/components/EmptyState";
import MetricCard from "@/components/MetricCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { staggerParent, staggerChild } from "@/lib/motion";
import {
  listAssignments, fetchReadiness, reviewBacklog, isOverdue,
  assignmentHandoffHref, RECIPIENT_STATE_LABEL, RECIPIENT_STATE_TONE,
} from "@/lib/assignments";
import type { UserTeam, TeamDashboard, Assignment, TeamReadiness, RecipientState } from "@/types";

const STATE_TONE_CLS: Record<"ink" | "warn" | "ok" | "danger" | "lav", string> = {
  ink: "border-hairline bg-surface-2 text-ink-subtle",
  warn: "border-warn/30 bg-warn/10 text-warn",
  ok: "border-ok/30 bg-ok/10 text-ok",
  danger: "border-danger/30 bg-danger/10 text-danger",
  lav: "border-lav/30 bg-lav/10 text-lav",
};

function stateBadge(status: RecipientState) {
  return (
    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${STATE_TONE_CLS[RECIPIENT_STATE_TONE[status]]}`}>
      {RECIPIENT_STATE_LABEL[status]}
    </span>
  );
}

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
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [readiness, setReadiness] = useState<TeamReadiness | null>(null);
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
      setAssignments([]);
      setReadiness(null);
      return;
    }

    setSelectedTeam(team);
    setDashboard(null);
    setAssignments([]);
    setReadiness(null);
    if (!userId) return;

    // Coaches load the roster + readiness; everyone loads their assignments.
    if (team.role === "coach") {
      apiFetch<TeamDashboard>(`/teams/${team.team_id}/dashboard?user_id=${userId}`)
        .then(setDashboard).catch(() => {});
      fetchReadiness(team.team_id).then(setReadiness).catch(() => {});
    }
    listAssignments(team.team_id).then(setAssignments).catch(() => {});
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
      <AppShell maxWidth="full" bare>
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
        </AppShell>
    );
  }

  if (err) {
    return (
      <AppShell maxWidth="full" bare>
          <div className="mx-auto max-w-4xl px-6 py-16">
            <p className="text-sm text-danger">{err}</p>
          </div>
        </AppShell>
    );
  }

  // No teams yet - show create/join cards
  if (teams.length === 0) {
    return (
      <AppShell maxWidth="full" bare>
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
        </AppShell>
    );
  }

  // Has teams - show team hub
  return (
    <AppShell maxWidth="full" bare>
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
                <MetricCard
                  label="Members"
                  value={dashboard.member_count}
                  icon={Users}
                  color="lav"
                />
                <MetricCard
                  label="Speeches"
                  value={dashboard.students.reduce((sum, s) => sum + s.speech_count, 0)}
                  icon={Mic}
                  color="ok"
                />
                <MetricCard
                  label="Drills"
                  value={dashboard.students.reduce((sum, s) => sum + s.drills_assigned_count, 0)}
                  icon={Target}
                  color="lav"
                />
                <MetricCard
                  label="Attempts"
                  value={dashboard.students.reduce((sum, s) => sum + s.drill_attempts_count, 0)}
                  icon={Headphones}
                  color="warn"
                />
              </motion.div>

              {/* Coach action bar + review backlog */}
              <motion.div variants={staggerChild} className="flex flex-col gap-3">
                {(() => {
                  const backlog = reviewBacklog(assignments);
                  const overdue = assignments.filter((a) => isOverdue(a)).length;
                  return (
                    <div className="flex flex-col gap-3 rounded-2xl border border-hairline bg-surface-1 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-eyebrow text-ink-subtle">Coach home</p>
                          <p className="text-sm font-semibold text-ink">
                            {backlog > 0
                              ? `${backlog} submission${backlog !== 1 ? "s" : ""} waiting for review`
                              : "You're all caught up on reviews"}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button asChild size="sm" className="gap-1.5">
                            <Link href={`/team/assign?team=${selectedTeam.team_id}`}><Plus size={12} /> New assignment</Link>
                          </Button>
                          <Button asChild size="sm" variant={backlog > 0 ? "default" : "secondary"} className="gap-1.5">
                            <Link href={`/team/review?team=${selectedTeam.team_id}`}><Inbox size={12} /> Review queue{backlog > 0 ? ` (${backlog})` : ""}</Link>
                          </Button>
                        </div>
                      </div>
                      {/* Readiness lanes */}
                      {readiness && readiness.recipient_total > 0 && (
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                          {[
                            { label: "Not started", value: readiness.assigned, tone: "text-ink-subtle" },
                            { label: "In progress", value: readiness.in_progress, tone: "text-lav" },
                            { label: "Ready for review", value: readiness.ready_for_review, tone: "text-warn" },
                            { label: "Reviewed", value: readiness.reviewed, tone: "text-ok" },
                          ].map((lane) => (
                            <div key={lane.label} className="flex flex-col gap-0.5 rounded-lg border border-hairline bg-surface-2/50 px-3 py-2">
                              <span className={`text-lg font-bold tabular-nums ${lane.tone}`}>{lane.value}</span>
                              <span className="text-[11px] text-ink-faint">{lane.label}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {overdue > 0 && (
                        <p className="flex items-center gap-1.5 text-xs text-warn">
                          <AlertTriangle size={12} aria-hidden /> {overdue} assignment{overdue !== 1 ? "s" : ""} past due with work outstanding.
                        </p>
                      )}
                    </div>
                  );
                })()}
              </motion.div>

              {/* Active assignments */}
              {assignments.length > 0 && (
                <motion.div variants={staggerChild} className="flex flex-col gap-2">
                  <p className="flex items-center gap-1.5 text-eyebrow text-ink-subtle"><ClipboardList size={12} aria-hidden /> Assignments</p>
                  {assignments.slice(0, 5).map((a) => {
                    const done = a.recipients.filter((r) => r.status === "reviewed" || r.status === "revision_requested").length;
                    return (
                      <Card key={a.id}>
                        <CardContent className="flex items-center gap-3 px-4 py-3">
                          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                            <span className="flex items-center gap-2">
                              <span className="truncate text-sm font-semibold text-ink">{a.title}</span>
                              {isOverdue(a) && <span className="shrink-0 rounded-full border border-warn/30 bg-warn/10 px-1.5 py-0.5 text-[9px] font-semibold text-warn">Overdue</span>}
                            </span>
                            <span className="text-xs text-ink-subtle">
                              {a.recipients.length} student{a.recipients.length !== 1 ? "s" : ""} · {done}/{a.recipients.length} reviewed
                              {a.due_date ? ` · due ${fmtDate(a.due_date)}` : ""}
                            </span>
                          </div>
                          {reviewBacklog([a]) > 0 && (
                            <Link href={`/team/review?team=${selectedTeam.team_id}`} className="shrink-0 text-xs font-medium text-lav hover:underline">
                              Review {reviewBacklog([a])} →
                            </Link>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </motion.div>
              )}

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
                      <Card key={student.user_id} className="transition-colors hover:border-hairline-strong">
                        <CardContent className="p-0">
                          <Link
                            href={`/team/student?team=${selectedTeam.team_id}&id=${student.user_id}`}
                            className="flex items-center gap-4 px-5 py-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
                          >
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
                            <ChevronRight size={15} className="shrink-0 text-ink-faint" aria-hidden />
                          </Link>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </motion.div>
            </>
          )}

          {/* Student View — assigned work */}
          {selectedTeam?.role === "student" && (
            <motion.div variants={staggerChild} className="flex flex-col gap-3">
              <p className="flex items-center gap-1.5 text-eyebrow text-ink-subtle"><ClipboardList size={12} aria-hidden /> Your assignments</p>
              {assignments.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center gap-3 px-5 py-8 text-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full border border-lav/20 bg-lav/10">
                      <Inbox size={20} className="text-lav" />
                    </div>
                    <p className="text-sm font-semibold text-ink">No assignments yet</p>
                    <p className="max-w-xs text-xs text-ink-subtle">When your coach assigns practice, it shows up here — ready to record in one tap.</p>
                    <Button asChild size="sm" variant="secondary"><Link href="/session">Practice on your own</Link></Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="flex flex-col gap-2">
                  {assignments.map((a) => {
                    const mine = a.recipients[0];
                    if (!mine) return null;
                    const actionable = mine.status === "assigned" || mine.status === "revision_requested";
                    return (
                      <Card key={a.id}>
                        <CardContent className="flex flex-col gap-2 px-5 py-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex min-w-0 flex-col gap-0.5">
                              <p className="truncate text-sm font-semibold text-ink">{a.title}</p>
                              <p className="text-xs text-ink-subtle">
                                {a.speech_type ? a.speech_type.replace("_", " ") : a.kind}
                                {a.judge_type ? ` · ${a.judge_type} judge` : ""}
                                {a.due_date ? ` · due ${fmtDate(a.due_date)}` : ""}
                              </p>
                            </div>
                            {stateBadge(mine.status)}
                          </div>
                          {a.goal && <p className="text-xs text-ink-subtle">Goal: {a.goal}</p>}
                          {mine.coach_feedback && (
                            <div className="rounded-lg border border-authored-coach/30 bg-authored-coach/[0.06] px-3 py-2">
                              <p className="text-[10px] font-semibold uppercase tracking-wide text-authored-coach">Coach feedback</p>
                              <p className="text-xs text-ink">{mine.coach_feedback}</p>
                            </div>
                          )}
                          {actionable ? (
                            <Button asChild size="sm" className="w-fit gap-1.5">
                              <Link href={assignmentHandoffHref(a, mine.id)}>
                                {mine.status === "revision_requested" ? "Redo & resubmit" : "Start assignment"} <ArrowRight size={12} />
                              </Link>
                            </Button>
                          ) : mine.submission_speech_id ? (
                            <Button asChild size="sm" variant="secondary" className="w-fit gap-1.5">
                              <Link href={`/speech/${mine.submission_speech_id}`}>View submission <ChevronRight size={12} /></Link>
                            </Button>
                          ) : null}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
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
                  <span className="font-medium text-ink-subtle">Need to leave a team?</span> Ask your coach to remove you — membership is managed by your team&apos;s coach.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </AppShell>
  );
}
