"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Plus, X, Check, Users } from "lucide-react";
import AppShell from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import DebateSide, { type SideValue } from "@/components/practice/DebateSide";
import { JudgeLensSelector, type JudgeValue } from "@/components/practice/JudgeLens";
import StickyActionDock from "@/components/practice/StickyActionDock";
import { SPEECH_TYPE_INFO, SPEECH_TYPE_ORDER } from "@/lib/practiceSetup";
import { createAssignment } from "@/lib/assignments";
import type { SpeechType, TeamDashboard } from "@/types";

export default function AssignmentBuilderPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [teamId, setTeamId] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<TeamDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadErr, setLoadErr] = useState("");

  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<"speech" | "rerecord">("speech");
  const [speechType, setSpeechType] = useState<SpeechType>("summary");
  const [side, setSide] = useState<SideValue>("");
  const [judge, setJudge] = useState<JudgeValue>("flow");
  const [topic, setTopic] = useState("");
  const [goal, setGoal] = useState("");
  const [criteria, setCriteria] = useState<string[]>([]);
  const [criterion, setCriterion] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [recipients, setRecipients] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    const tid = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("team") : null;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time URL init, hydration-safe
    setTeamId(tid);
    createClient().auth.getUser()
      .then(async ({ data }) => {
        if (!data.user) { router.replace("/login"); return; }
        setUserId(data.user.id);
        if (!tid) { setLoadErr("No team selected."); return; }
        const dash = await apiFetch<TeamDashboard>(`/teams/${tid}/dashboard?user_id=${data.user.id}`);
        setDashboard(dash);
      })
      .catch(() => setLoadErr("Could not load the team. You may not have coach access."))
      .finally(() => setLoading(false));
  }, [router]);

  function toggleRecipient(id: string) {
    setRecipients((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function addCriterion() {
    const c = criterion.trim();
    if (!c) return;
    setCriteria((p) => [...p, c]);
    setCriterion("");
  }

  async function handleCreate() {
    if (!userId || !teamId) return;
    if (!title.trim()) { setErr("Give the assignment a title."); return; }
    if (recipients.size === 0) { setErr("Select at least one student."); return; }
    setErr(""); setSubmitting(true);
    try {
      await createAssignment({
        team_id: teamId, title: title.trim(), kind,
        speech_type: speechType, side: side || null, judge_type: judge || null,
        topic: topic || null, goal: goal || null, success_criteria: criteria,
        due_date: dueDate || null, recipient_user_ids: Array.from(recipients),
      });
      router.push("/team");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Could not create the assignment.");
      setSubmitting(false);
    }
  }

  const students = dashboard?.students ?? [];

  return (
    <AppShell maxWidth="full" bare>
      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 sm:px-6">
        <div className="flex flex-col gap-1">
          <Link href="/team" className="flex w-fit items-center gap-1 text-xs text-ink-subtle transition-colors hover:text-ink">
            <ArrowLeft size={12} aria-hidden /> Back to team
          </Link>
          <h1 className="text-title text-ink">New assignment</h1>
          <p className="text-sm text-ink-subtle">Set the practice, pick who does it, and RoundLab hands the context straight into their recorder.</p>
        </div>

        {loading ? (
          <div className="flex flex-col gap-4">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}</div>
        ) : loadErr ? (
          <p className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">{loadErr}</p>
        ) : (
          <>
            <section className="flex flex-col gap-3">
              <label htmlFor="a-title" className="text-xs font-medium text-ink-subtle">Title</label>
              <Input id="a-title" placeholder="e.g. Summary collapse before Saturday" value={title} onChange={(e) => setTitle(e.target.value)} />
            </section>

            <section className="flex flex-col gap-2">
              <span className="text-xs font-medium text-ink-subtle">Practice type</span>
              <div className="flex gap-0.5 rounded-lg border border-hairline bg-surface-2 p-0.5" role="radiogroup" aria-label="Assignment kind">
                {([["speech", "New speech"], ["rerecord", "Re-record"]] as const).map(([val, label]) => (
                  <button key={val} type="button" role="radio" aria-checked={kind === val}
                    onClick={() => setKind(val)}
                    className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 ${kind === val ? "bg-surface-3 text-ink" : "text-ink-subtle hover:text-ink"}`}>
                    {label}
                  </button>
                ))}
              </div>
              <div role="radiogroup" aria-label="Speech type" className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {SPEECH_TYPE_ORDER.map((t) => (
                  <button key={t} type="button" role="radio" aria-checked={speechType === t}
                    onClick={() => setSpeechType(t)}
                    className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 ${speechType === t ? "border-lav/50 bg-lav/[0.07] text-ink" : "border-hairline bg-surface-1 text-ink-subtle hover:text-ink"}`}>
                    {SPEECH_TYPE_INFO[t].label}
                  </button>
                ))}
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-medium text-ink-subtle">Side</span>
                <DebateSide value={side} onChange={setSide} allowUnset />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="a-due" className="text-xs font-medium text-ink-subtle">Due date</label>
                <Input id="a-due" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>
            </section>

            <section className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-ink-subtle">Judge lens</span>
              <JudgeLensSelector value={judge} onChange={setJudge} />
            </section>

            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="a-topic" className="text-xs font-medium text-ink-subtle">Resolution</label>
                <Input id="a-topic" placeholder="Resolved: …" value={topic} onChange={(e) => setTopic(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="a-goal" className="text-xs font-medium text-ink-subtle">Goal</label>
                <Input id="a-goal" placeholder="What should they focus on?" value={goal} onChange={(e) => setGoal(e.target.value)} />
              </div>
            </section>

            <section className="flex flex-col gap-2">
              <span className="text-xs font-medium text-ink-subtle">Success criteria</span>
              <div className="flex gap-2">
                <Input placeholder="Add a criterion…" value={criterion}
                  onChange={(e) => setCriterion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCriterion(); } }} />
                <Button type="button" variant="secondary" size="sm" onClick={addCriterion} className="shrink-0 gap-1"><Plus size={12} /> Add</Button>
              </div>
              {criteria.length > 0 && (
                <ul className="flex flex-col gap-1">
                  {criteria.map((c, i) => (
                    <li key={i} className="flex items-center gap-2 rounded-md border border-hairline bg-surface-1 px-2.5 py-1.5 text-xs text-ink">
                      <Check size={11} className="shrink-0 text-ok" aria-hidden /> <span className="flex-1">{c}</span>
                      <button type="button" onClick={() => setCriteria((p) => p.filter((_, j) => j !== i))} aria-label="Remove criterion" className="text-ink-faint hover:text-danger"><X size={12} /></button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="flex flex-col gap-2">
              <span className="flex items-center gap-1.5 text-xs font-medium text-ink-subtle">
                <Users size={12} aria-hidden /> Recipients ({recipients.size} selected)
              </span>
              {students.length === 0 ? (
                <p className="rounded-lg border border-hairline bg-surface-1 px-3 py-4 text-xs text-ink-subtle">No students on this team yet — share your invite code first.</p>
              ) : (
                <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {students.map((s) => {
                    const on = recipients.has(s.user_id);
                    const name = s.display_name || `Student ${s.user_id.slice(0, 6)}`;
                    return (
                      <li key={s.user_id}>
                        <button type="button" onClick={() => toggleRecipient(s.user_id)} aria-pressed={on}
                          className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 ${on ? "border-lav/50 bg-lav/[0.07]" : "border-hairline bg-surface-1 hover:border-hairline-strong"}`}>
                          <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${on ? "border-lav bg-lav text-white" : "border-hairline-strong"}`}>{on && <Check size={11} />}</span>
                          <span className="truncate text-ink">{name}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            {err && <p className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">{err}</p>}

            <StickyActionDock
              summary={<span className="text-xs text-ink-subtle">{SPEECH_TYPE_INFO[speechType].label}{judge ? ` · ${judge} judge` : ""} · {recipients.size} student{recipients.size !== 1 ? "s" : ""}</span>}
            >
              <Button onClick={handleCreate} disabled={submitting} className="gap-2">
                {submitting ? "Assigning…" : (<>Assign to students <ArrowRight size={14} /></>)}
              </Button>
            </StickyActionDock>
          </>
        )}
      </div>
    </AppShell>
  );
}
