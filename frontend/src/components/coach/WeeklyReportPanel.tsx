"use client";

import { useState, useRef } from "react";
import { Download, Printer, Users, Mic, BookOpen, ClipboardCheck, TrendingUp, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchWeeklyReport } from "@/lib/coachApi";
import type { WeeklyReport } from "@/types/coach";
import { SKILL_LABEL } from "@/types/coach";

interface Props {
  teamId: string;
  teamName: string;
}

function Row({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string | number; sub?: string }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-hairline last:border-0">
      <span className="text-ink-subtle shrink-0">{icon}</span>
      <span className="flex-1 text-[13px] text-ink">{label}</span>
      <span className="text-[13px] font-semibold tabular-nums text-ink">{value}</span>
      {sub && <span className="text-[11px] text-ink-subtle">{sub}</span>}
    </div>
  );
}

function csvFromReport(report: WeeklyReport, teamName: string): string {
  const header = ["Student", "Speeches this week", "Drills this week", "Active skill"];
  const rows = report.roster.map((r) => [
    r.display_name ?? "Student",
    r.speeches_this_week,
    r.drills_this_week,
    r.active_mission_skill ? (SKILL_LABEL[r.active_mission_skill] ?? r.active_mission_skill) : "—",
  ]);
  const csv = [header, ...rows].map((r) => r.map(String).map((v) => `"${v.replace(/"/g, '""')}"`).join(",")).join("\n");
  return `Dissio Weekly Report — ${teamName}\nPeriod: ${report.period_start.slice(0, 10)} to ${report.period_end.slice(0, 10)}\n\n${csv}`;
}

export default function WeeklyReportPanel({ teamId, teamName }: Props) {
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const reportRef = useRef<HTMLDivElement>(null);

  async function generate() {
    setLoading(true);
    setErr("");
    try {
      const r = await fetchWeeklyReport(teamId);
      setReport(r);
    } catch {
      setErr("Failed to generate report. Try again.");
    } finally {
      setLoading(false);
    }
  }

  function handlePrint() {
    window.print();
  }

  function handleCsv() {
    if (!report) return;
    const csv = csvFromReport(report, teamName);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dissio-weekly-${report.period_end.slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!report && !loading) {
    return (
      <div className="rounded-xl border border-hairline bg-surface-2 px-6 py-8 text-center">
        <p className="mb-1 text-[13px] font-medium text-ink">Generate weekly team report</p>
        <p className="mb-4 text-[12px] text-ink-subtle">
          Participation, assignments, drills, and improvement summary for the past 7 days.
        </p>
        {err && <p className="mb-3 text-[12px] text-danger">{err}</p>}
        <Button size="sm" onClick={generate} disabled={loading}>
          {loading ? "Generating…" : "Generate report"}
        </Button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-2 animate-pulse" aria-busy="true" aria-label="Generating report">
        {[1, 2, 3, 4].map((i) => <div key={i} className="h-10 rounded-xl bg-surface-2" />)}
      </div>
    );
  }

  if (!report) return null;

  const startDate = new Date(report.period_start).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const endDate = new Date(report.period_end).toLocaleDateString(undefined, { month: "short", day: "numeric" });

  return (
    <div className="space-y-4" ref={reportRef}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[13px] font-semibold text-ink">Weekly Report — {teamName}</p>
          <p className="text-[11px] text-ink-subtle">{startDate} – {endDate}</p>
        </div>
        <div className="flex gap-2 print:hidden">
          <Button size="sm" variant="outline" onClick={handleCsv}>
            <Download size={13} aria-hidden className="mr-1" /> CSV
          </Button>
          <Button size="sm" variant="outline" onClick={handlePrint}>
            <Printer size={13} aria-hidden className="mr-1" /> Print
          </Button>
          <Button size="sm" variant="outline" onClick={generate}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary metrics */}
      <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-2">
        <Row icon={<Users size={14} />} label="Participated" value={`${report.students_participated} / ${report.total_students}`} />
        <Row icon={<Mic size={14} />} label="Speeches analyzed" value={report.speeches_analyzed} />
        <Row icon={<BookOpen size={14} />} label="Drills completed" value={report.drills_completed} />
        <Row icon={<ClipboardCheck size={14} />} label="Assignments reviewed" value={report.assignments_completed} />
        <Row icon={<TrendingUp size={14} />} label="Students improving" value={report.students_improving} />
        <Row icon={<AlertTriangle size={14} />} label="Need attention" value={report.students_needing_attention} />
      </div>

      {/* Common weakness */}
      {report.common_team_weakness && (
        <div className="rounded-xl border border-lav/30 bg-lav/5 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-lav">Team-wide skill focus</p>
          <p className="mt-0.5 text-[13px] text-ink">
            {SKILL_LABEL[report.common_team_weakness] ?? report.common_team_weakness}
          </p>
        </div>
      )}

      {/* Recommended focus */}
      <div className="rounded-xl border border-hairline bg-surface-2 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">Next practice focus</p>
        <p className="mt-0.5 text-[13px] text-ink">{report.recommended_focus}</p>
      </div>

      {/* Roster table */}
      {report.roster.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-hairline">
          <table className="w-full min-w-[400px] border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-hairline bg-surface-2 text-left text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
                <th className="px-3 py-2">Student</th>
                <th className="px-3 py-2 text-center">Speeches</th>
                <th className="px-3 py-2 text-center">Drills</th>
                <th className="px-3 py-2">Active skill</th>
              </tr>
            </thead>
            <tbody>
              {report.roster.map((r) => (
                <tr key={r.user_id} className="border-b border-hairline last:border-0">
                  <td className="px-3 py-2 font-medium text-ink">{r.display_name ?? "Student"}</td>
                  <td className="px-3 py-2 text-center tabular-nums text-ink-subtle">{r.speeches_this_week}</td>
                  <td className="px-3 py-2 text-center tabular-nums text-ink-subtle">{r.drills_this_week}</td>
                  <td className="px-3 py-2 text-ink-subtle">
                    {r.active_mission_skill
                      ? SKILL_LABEL[r.active_mission_skill] ?? r.active_mission_skill
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
