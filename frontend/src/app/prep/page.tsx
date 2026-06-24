"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  BarChart3,
  AlertTriangle,
  Droplets,
  Clipboard,
  Dumbbell,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { ReadinessOverview } from "@/components/prep/ReadinessOverview";
import { FreshnessPanel } from "@/components/prep/FreshnessPanel";
import { PrepPlanPanel } from "@/components/prep/PrepPlanPanel";
import { PrepWorkoutPanel } from "@/components/prep/PrepWorkoutPanel";
import { GapsPanel } from "@/components/prep/GapsPanel";
import type {
  PrepReadinessReport,
  PrepTask,
  PrepWorkout,
  PrepWorkspace,
} from "@/types/prep";

type Tab = "overview" | "gaps" | "freshness" | "plan" | "workouts";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <BarChart3 size={14} /> },
  { id: "gaps", label: "Gaps", icon: <AlertTriangle size={14} /> },
  { id: "freshness", label: "Freshness", icon: <Droplets size={14} /> },
  { id: "plan", label: "Prep Plan", icon: <Clipboard size={14} /> },
  { id: "workouts", label: "Workouts", icon: <Dumbbell size={14} /> },
];

function EmptyState({ onGenerate, loading }: { onGenerate: () => void; loading: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 space-y-4">
      <BarChart3 size={40} className="text-ink-faint" />
      <p className="text-[16px] font-semibold text-ink">Tournament Prep</p>
      <p className="text-[13px] text-ink-subtle text-center max-w-sm">
        Generate a readiness report to see how prepared your case is, find evidence gaps, and get
        gap-driven drills.
      </p>
      <button
        onClick={onGenerate}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-lav text-white rounded-lg text-[13px] hover:bg-lav/80 disabled:opacity-50 transition-colors"
      >
        {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
        {loading ? "Generating…" : "Generate Report"}
      </button>
    </div>
  );
}

function PrepPageContent() {
  const searchParams = useSearchParams();
  const workspaceId = searchParams.get("workspace");
  const resolutionId = searchParams.get("resolution");
  const side = (searchParams.get("side") as "pro" | "con" | "both") || "pro";

  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [report, setReport] = useState<PrepReadinessReport | null>(null);
  const [tasks, setTasks] = useState<PrepTask[]>([]);
  const [workouts, setWorkouts] = useState<PrepWorkout[]>([]);
  const [workspace, setWorkspace] = useState<PrepWorkspace | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mock user_id; in real app from auth context
  const userId =
    typeof window !== "undefined"
      ? localStorage.getItem("user_id") || "demo-user"
      : "demo-user";

  const ensureWorkspace = useCallback(async (): Promise<string> => {
    if (workspaceId) return workspaceId;
    if (!resolutionId) throw new Error("No resolution selected");
    const ws = (await apiFetch("/prep/workspaces", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        resolution_id: resolutionId,
        side,
      }),
    })) as PrepWorkspace;
    setWorkspace(ws);
    return ws.id;
  }, [workspaceId, resolutionId, side, userId]);

  const loadWorkspace = useCallback(async (wsId: string) => {
    try {
      const data = (await apiFetch(
        `/prep/workspaces/${wsId}/overview?user_id=${userId}`
      )) as {
        workspace: PrepWorkspace;
        latest_report: PrepReadinessReport | null;
        pending_tasks: PrepTask[];
        active_workouts: PrepWorkout[];
      };
      setWorkspace(data.workspace);
      if (data.latest_report) setReport(data.latest_report);
      setTasks(data.pending_tasks);
      setWorkouts(data.active_workouts);
    } catch {
      // No workspace yet
    }
  }, [userId]);

  useEffect(() => {
    if (workspaceId) {
      void loadWorkspace(workspaceId);
    }
  }, [workspaceId, loadWorkspace]);

  async function generateReport() {
    setLoading(true);
    setError(null);
    try {
      const wsId = await ensureWorkspace();
      const rep = (await apiFetch("/prep/readiness-report", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: wsId,
          user_id: userId,
          force_refresh: false,
        }),
      })) as PrepReadinessReport;
      setReport(rep);

      // Auto-generate plan
      if (rep.id) {
        try {
          const plan = (await apiFetch("/prep/prep-plan", {
            method: "POST",
            body: JSON.stringify({
              workspace_id: wsId,
              user_id: userId,
              report_id: rep.id,
            }),
          })) as { tasks: PrepTask[]; workouts: PrepWorkout[] };
          setTasks(plan.tasks || []);
          setWorkouts(plan.workouts || []);
        } catch {
          // Plan generation non-fatal
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setLoading(false);
    }
  }

  function handleTaskComplete(id: string) {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: "completed" as const } : t))
    );
  }

  function handleWorkoutComplete(id: string) {
    setWorkouts((prev) =>
      prev.map((w) => (w.id === id ? { ...w, status: "completed" as const } : w))
    );
  }

  if (!resolutionId && !workspaceId) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12">
        <p className="text-[14px] text-ink-subtle text-center">
          Open Tournament Prep from a resolution in your Evidence Library.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-bold text-ink">Tournament Prep</h1>
          {workspace && (
            <p className="text-[12px] text-ink-subtle capitalize">
              {workspace.side === "both" ? "Pro + Con" : workspace.side} ·{" "}
              {workspace.tournament_date
                ? `Tournament ${workspace.tournament_date}`
                : "No date set"}
            </p>
          )}
        </div>
        <button
          onClick={generateReport}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] border border-border hover:border-lav text-ink hover:text-lav transition-colors disabled:opacity-50"
        >
          {loading ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <RefreshCw size={12} />
          )}
          {loading ? "Generating…" : report ? "Refresh" : "Generate"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3">
          <p className="text-[12px] text-danger">{error}</p>
        </div>
      )}

      {!report && !loading && (
        <EmptyState onGenerate={generateReport} loading={loading} />
      )}

      {report && (
        <>
          {/* Tabs */}
          <div className="flex gap-1 border-b border-border pb-0">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 text-[12px] border-b-2 -mb-px transition-colors ${
                  activeTab === tab.id
                    ? "border-lav text-lav font-semibold"
                    : "border-transparent text-ink-subtle hover:text-ink"
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.id === "gaps" && report.gaps.length > 0 && (
                  <span className="ml-0.5 text-[9px] bg-lav/10 text-lav px-1 rounded-full">
                    {report.gaps.length}
                  </span>
                )}
                {tab.id === "plan" && tasks.filter((t) => t.status === "pending").length > 0 && (
                  <span className="ml-0.5 text-[9px] bg-amber-100 text-amber-700 px-1 rounded-full">
                    {tasks.filter((t) => t.status === "pending").length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="min-h-[400px]">
            {activeTab === "overview" && <ReadinessOverview report={report} />}
            {activeTab === "gaps" && <GapsPanel gaps={report.gaps} />}
            {activeTab === "freshness" && (
              <FreshnessPanel assessments={report.freshness_assessments} />
            )}
            {activeTab === "plan" && (
              <PrepPlanPanel tasks={tasks} onTaskComplete={handleTaskComplete} />
            )}
            {activeTab === "workouts" && (
              <PrepWorkoutPanel
                workouts={workouts}
                onWorkoutComplete={handleWorkoutComplete}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function PrepPage() {
  return (
    <Suspense fallback={<div className="max-w-5xl mx-auto px-4 py-8 text-sm text-[var(--ink-subtle)]">Loading…</div>}>
      <PrepPageContent />
    </Suspense>
  );
}
