"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Users, Copy, Check, Plus,
  ClipboardList, Inbox, BarChart2, BookTemplate, BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { fetchCommandCenter } from "@/lib/coachApi";
import { fetchReadiness, reviewBacklog, listAssignments } from "@/lib/assignments";
import TeamStatusSummary from "@/components/coach/TeamStatusSummary";
import AttentionQueue from "@/components/coach/AttentionQueue";
import StudentRosterTable from "@/components/coach/StudentRosterTable";
import AssignmentTemplatePanel from "@/components/coach/AssignmentTemplatePanel";
import WeeklyReportPanel from "@/components/coach/WeeklyReportPanel";
import CurriculumPanel from "@/components/coach/CurriculumPanel";
import type { UserTeam, Assignment } from "@/types";
import type { CommandCenterData } from "@/types/coach";

type Panel = "roster" | "attention" | "templates" | "report" | "curriculum";

export default function TeamPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [teams, setTeams] = useState<UserTeam[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<UserTeam | null>(null);
  const [cmdCenter, setCmdCenter] = useState<CommandCenterData | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [cmdLoading, setCmdLoading] = useState(false);
  const [err, setErr] = useState("");
  const [panel, setPanel] = useState<Panel>("roster");

  // Create/join state
  const [creating, setCreating] = useState(false);
  const [joining, setJoining] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [formErr, setFormErr] = useState("");
  const [formLoading, setFormLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);
        const userTeams = await apiFetch<UserTeam[]>(`/teams/users/${data.user.id}`);
        setTeams(userTeams);
        if (userTeams.length === 1) {
          loadTeam(userTeams[0]);
        }
      })
      .catch(() => setErr("Could not load team data."))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const loadTeam = useCallback(async (team: UserTeam) => {
    setSelectedTeam(team);
    setCmdCenter(null);
    setCmdLoading(true);
    try {
      if (team.role === "coach") {
        const [cc, a] = await Promise.all([
          fetchCommandCenter(team.team_id).catch(() => null),
          listAssignments(team.team_id).catch(() => []),
        ]);
        setCmdCenter(cc);
        setAssignments(a);
      } else {
        const a = await listAssignments(team.team_id).catch(() => []);
        setAssignments(a);
      }
    } finally {
      setCmdLoading(false);
    }
  }, []);

  async function createTeam() {
    if (!newTeamName.trim() || !userId) return;
    setFormLoading(true);
    setFormErr("");
    try {
      const team = await apiFetch<{ id: string; name: string; invite_code: string; created_by: string; created_at: string }>("/teams", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newTeamName.trim(), created_by: userId }),
      });
      const newEntry: UserTeam = { team_id: team.id, team_name: team.name, role: "coach", invite_code: team.invite_code };
      setTeams((prev) => [...prev, newEntry]);
      setNewTeamName("");
      setCreating(false);
      loadTeam(newEntry);
    } catch {
      setFormErr("Failed to create team.");
    } finally {
      setFormLoading(false);
    }
  }

  async function joinTeam() {
    if (!joinCode.trim() || !userId) return;
    setFormLoading(true);
    setFormErr("");
    try {
      await apiFetch("/teams/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invite_code: joinCode.trim().toUpperCase(), user_id: userId }),
      });
      const updated = await apiFetch<UserTeam[]>(`/teams/users/${userId}`);
      setTeams(updated);
      setJoinCode("");
      setJoining(false);
    } catch {
      setFormErr("Invalid invite code or already a member.");
    } finally {
      setFormLoading(false);
    }
  }

  function copyInvite() {
    if (!selectedTeam) return;
    navigator.clipboard.writeText(selectedTeam.invite_code).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  const isCoach = selectedTeam?.role === "coach";
  const backlog = reviewBacklog(assignments);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8 space-y-4">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
      </div>
    );
  }

  if (!loading && teams.length === 0 && !creating && !joining) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16 sm:px-6 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-lav/10 mb-2">
          <Users size={22} className="text-lav" aria-hidden />
        </div>
        <h1 className="text-xl font-bold text-ink">Start a team</h1>
        <p className="text-[13px] text-ink-subtle">
          Create a program and invite students, or join with a code your coach shared.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Button size="sm" onClick={() => setCreating(true)}>
            <Plus size={14} className="mr-1.5" aria-hidden /> Create team
          </Button>
          <Button size="sm" variant="outline" onClick={() => setJoining(true)}>
            Join with invite code
          </Button>
        </div>
      </div>
    );
  }

  if (creating || joining) {
    return (
      <div className="mx-auto max-w-sm px-4 py-16 sm:px-6 space-y-4">
        <h1 className="text-lg font-bold text-ink">
          {creating ? "Create your team" : "Join a team"}
        </h1>
        {creating ? (
          <div className="space-y-3">
            <Input
              placeholder="Program name (e.g. Jefferson Debate)"
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createTeam()}
              aria-label="Team name"
            />
            {formErr && <p className="text-[12px] text-danger">{formErr}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={createTeam} disabled={formLoading || !newTeamName.trim()}>
                {formLoading ? "Creating…" : "Create"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setCreating(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <Input
              placeholder="Invite code (e.g. ABC12345)"
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === "Enter" && joinTeam()}
              aria-label="Invite code"
            />
            {formErr && <p className="text-[12px] text-danger">{formErr}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={joinTeam} disabled={formLoading || !joinCode.trim()}>
                {formLoading ? "Joining…" : "Join"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setJoining(false)}>Cancel</Button>
            </div>
          </div>
        )}
      </div>
    );
  }

  const TeamPicker = () => (
    <div className="flex flex-wrap gap-2 items-center">
      {teams.map((t) => (
        <button
          key={t.team_id}
          onClick={() => loadTeam(t)}
          className={`rounded-full border px-3 py-1 text-[12px] font-medium transition-colors ${
            selectedTeam?.team_id === t.team_id
              ? "border-lav bg-lav/10 text-lav"
              : "border-hairline bg-surface-2 text-ink-subtle hover:text-ink"
          }`}
          aria-pressed={selectedTeam?.team_id === t.team_id}
        >
          {t.team_name}
          <span className="ml-1 text-[10px] opacity-60">({t.role})</span>
        </button>
      ))}
      <button
        onClick={() => setCreating(true)}
        className="rounded-full border border-dashed border-hairline px-2.5 py-1 text-[11px] text-ink-subtle hover:text-ink"
        aria-label="Create new team"
      >
        <Plus size={11} className="inline mr-0.5" aria-hidden /> New
      </button>
      <button
        onClick={() => setJoining(true)}
        className="rounded-full border border-dashed border-hairline px-2.5 py-1 text-[11px] text-ink-subtle hover:text-ink"
        aria-label="Join team with code"
      >
        Join
      </button>
    </div>
  );

  if (err) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        {teams.length > 1 && <div className="mb-6"><TeamPicker /></div>}
        <p className="text-[13px] text-danger">{err}</p>
      </div>
    );
  }

  // Student view
  if (selectedTeam && !isCoach) {
    const myAssignments = assignments.filter((a) => a.recipients.length > 0);
    return (
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        {teams.length > 1 && <TeamPicker />}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-ink">{selectedTeam.team_name}</h1>
          <span className="rounded-full border border-hairline px-2.5 py-0.5 text-[11px] text-ink-subtle">Student</span>
        </div>
        {myAssignments.length === 0 ? (
          <div className="rounded-xl border border-hairline bg-surface-2 px-4 py-8 text-center text-[13px] text-ink-subtle">
            No assignments yet. Check back after your coach creates one.
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">Your assignments</p>
            {myAssignments.map((a) => {
              const mine = a.recipients[0];
              return (
                <div key={a.id} className="rounded-xl border border-hairline bg-surface-1 px-4 py-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[13px] font-medium text-ink">{a.title}</p>
                      {a.goal && <p className="text-[12px] text-ink-subtle mt-0.5">{a.goal}</p>}
                    </div>
                    <span className="shrink-0 rounded-full border border-hairline px-2 py-0.5 text-[10px] font-semibold text-ink-subtle">
                      {mine?.status ?? "assigned"}
                    </span>
                  </div>
                  {mine?.coach_feedback && (
                    <div className="mt-2 rounded-lg bg-surface-2 px-3 py-2 text-[12px] text-ink-subtle">
                      <span className="font-semibold">Coach: </span>{mine.coach_feedback}
                    </div>
                  )}
                  {mine && mine.status === "assigned" && (
                    <Link
                      href={`/session?assignment=${mine.id}&type=${a.speech_type ?? ""}`}
                      className="mt-2 inline-block rounded-lg bg-lav px-3 py-1.5 text-[12px] font-medium text-white hover:bg-lav/90"
                    >
                      Start assignment →
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Coach Command Center
  const cmdRoster = cmdCenter?.roster ?? [];
  const studentPreviews = cmdRoster.map((r) => ({ user_id: r.user_id, display_name: r.display_name }));

  const PANELS: { id: Panel; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: "roster", label: "Roster", icon: <Users size={14} aria-hidden /> },
    { id: "attention", label: "Attention", icon: <Inbox size={14} aria-hidden />, badge: cmdCenter?.attention_queue.length },
    { id: "templates", label: "Assign", icon: <BookTemplate size={14} aria-hidden /> },
    { id: "curriculum", label: "Curriculum", icon: <BookOpen size={14} aria-hidden /> },
    { id: "report", label: "Report", icon: <BarChart2 size={14} aria-hidden /> },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {teams.length > 1 && <TeamPicker />}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-ink" aria-label="Coach Command Center">
            {selectedTeam?.team_name ?? "Command Center"}
          </h1>
          <p className="text-[12px] text-ink-subtle mt-0.5">Coach overview</p>
        </div>
        <div className="flex items-center gap-2">
          {selectedTeam && (
            <button
              onClick={copyInvite}
              className="flex items-center gap-1.5 rounded-lg border border-hairline bg-surface-2 px-3 py-1.5 text-[12px] text-ink-subtle hover:bg-surface-3 hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-lav"
              aria-label={`Copy invite code ${selectedTeam.invite_code}`}
            >
              {copied ? <Check size={13} className="text-ok" aria-hidden /> : <Copy size={13} aria-hidden />}
              {selectedTeam.invite_code}
            </button>
          )}
          <Link
            href={`/team/assign${selectedTeam ? `?team=${selectedTeam.team_id}` : ""}`}
            className="rounded-lg bg-lav px-3 py-1.5 text-[12px] font-medium text-white hover:bg-lav/90 transition-colors focus-visible:outline-2 focus-visible:outline-white"
          >
            <Plus size={13} className="inline mr-1" aria-hidden /> Assign
          </Link>
          {backlog > 0 && (
            <Link
              href={`/team/review${selectedTeam ? `?team=${selectedTeam.team_id}` : ""}`}
              className="flex items-center gap-1.5 rounded-lg border border-warn/30 bg-warn/10 px-3 py-1.5 text-[12px] font-medium text-warn hover:bg-warn/20 transition-colors focus-visible:outline-2 focus-visible:outline-warn"
            >
              <ClipboardList size={13} aria-hidden />
              Review {backlog}
            </Link>
          )}
        </div>
      </div>

      {cmdLoading ? (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6" aria-busy="true" aria-label="Loading team summary">
          {[1,2,3,4,5,6].map((i) => <Skeleton key={i} className="h-14" />)}
        </div>
      ) : cmdCenter ? (
        <TeamStatusSummary summary={cmdCenter.summary} />
      ) : null}

      {selectedTeam && (
        <>
          <div
            className="flex gap-1 border-b border-hairline"
            role="tablist"
            aria-label="Coach Command Center panels"
          >
            {PANELS.map((p) => (
              <button
                key={p.id}
                role="tab"
                aria-selected={panel === p.id}
                aria-controls={`panel-${p.id}`}
                id={`tab-${p.id}`}
                onClick={() => setPanel(p.id)}
                className={`relative flex items-center gap-1.5 px-3 pb-2 pt-1 text-[12px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-lav ${
                  panel === p.id
                    ? "text-lav border-b-2 border-lav -mb-px"
                    : "text-ink-subtle hover:text-ink"
                }`}
              >
                {p.icon}
                {p.label}
                {p.badge !== undefined && p.badge > 0 && (
                  <span className="rounded-full bg-warn px-1.5 py-0.5 text-[9px] font-bold text-white leading-none">
                    {p.badge}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div
            role="tabpanel"
            id={`panel-${panel}`}
            aria-labelledby={`tab-${panel}`}
          >
            {panel === "roster" && (
              cmdLoading ? (
                <div className="space-y-2" aria-busy="true">
                  {[1,2,3].map((i) => <Skeleton key={i} className="h-10" />)}
                </div>
              ) : (
                <StudentRosterTable
                  roster={cmdCenter?.roster ?? []}
                  teamId={selectedTeam.team_id}
                />
              )
            )}
            {panel === "attention" && (
              cmdLoading ? (
                <div className="space-y-2" aria-busy="true">
                  {[1,2].map((i) => <Skeleton key={i} className="h-12" />)}
                </div>
              ) : (
                <AttentionQueue
                  queue={cmdCenter?.attention_queue ?? []}
                  teamId={selectedTeam.team_id}
                />
              )
            )}
            {panel === "templates" && (
              <AssignmentTemplatePanel
                teamId={selectedTeam.team_id}
                students={studentPreviews}
                onAssigned={() => {
                  listAssignments(selectedTeam.team_id).then(setAssignments).catch(() => {});
                }}
              />
            )}
            {panel === "curriculum" && userId && (
              <CurriculumPanel
                teamId={selectedTeam.team_id}
                coachId={userId}
              />
            )}
            {panel === "report" && (
              <WeeklyReportPanel
                teamId={selectedTeam.team_id}
                teamName={selectedTeam.team_name}
              />
            )}
          </div>
        </>
      )}

      {!selectedTeam && !loading && teams.length > 0 && (
        <div className="rounded-xl border border-hairline bg-surface-2 px-4 py-8 text-center text-[13px] text-ink-subtle">
          Select a team above to view the Command Center.
        </div>
      )}
    </div>
  );
}
