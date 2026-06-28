"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { ApiError } from "@/lib/api";
import * as roundApi from "@/lib/roundApi";
import { RoundSetupForm } from "@/components/round/RoundSetupForm";
import { RoundPhaseHeader } from "@/components/round/RoundPhaseHeader";
import { RoundFlow } from "@/components/round/RoundFlow";
import { RoundSpeechCapture } from "@/components/round/RoundSpeechCapture";
import { RoundBallotView } from "@/components/round/RoundBallotView";
import { RoundDrillsView } from "@/components/round/RoundDrillsView";
import type {
  RoundArgument,
  RoundDecision,
  RoundDrill,
  RoundSimulation,
  RoundSimulationConfig,
  RoundSpeech,
  RoundStateResponse,
} from "@/types/round";

type View = "setup" | "round" | "flow" | "evidence" | "ballot" | "drills";
type AuthState = "loading" | "signed-in" | "signed-out";

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mx-4 mt-3 rounded-md border border-red-200 bg-red-50 dark:bg-red-950/20 px-3 py-2 flex items-start justify-between gap-2">
      <p className="text-xs text-red-700 dark:text-red-400">{message}</p>
      <button onClick={onDismiss} className="text-red-400 hover:text-red-600 text-xs shrink-0">✕</button>
    </div>
  );
}

export default function RoundSimulationPage() {
  const router = useRouter();
  const [authState, setAuthState] = useState<AuthState>("loading");

  const [view, setView] = useState<View>("setup");
  const [simulation, setSimulation] = useState<RoundSimulation | null>(null);
  const [roundState, setRoundState] = useState<RoundStateResponse | null>(null);
  const [speeches, setSpeeches] = useState<RoundSpeech[]>([]);
  const [flowArgs, setFlowArgs] = useState<RoundArgument[]>([]);
  const [decision, setDecision] = useState<RoundDecision | null>(null);
  const [drills, setDrills] = useState<RoundDrill[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Auth check ──────────────────────────────────────────────────────────────

  useEffect(() => {
    const sb = createClient();
    sb.auth.getSession().then(({ data }) => {
      setAuthState(data.session ? "signed-in" : "signed-out");
    });
    const { data: sub } = sb.auth.onAuthStateChange((_event, session) => {
      setAuthState(session ? "signed-in" : "signed-out");
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  // ── Recover round from localStorage ────────────────────────────────────────

  useEffect(() => {
    if (authState !== "signed-in") return;
    // Read from new key, fall back to legacy key and migrate
    const saved = typeof window !== "undefined"
      ? localStorage.getItem("dissio_active_round") ??
        (() => { const v = localStorage.getItem("roundlab_active_round"); if (v) { localStorage.setItem("dissio_active_round", v); localStorage.removeItem("roundlab_active_round"); } return v; })()
      : null;
    if (!saved) return;
    // Silently try to recover; clear if not found
    roundApi.getRoundState(saved).then((state) => {
      if (state.simulation.status !== "completed" && state.simulation.status !== "abandoned") {
        setRoundState(state);
        setSimulation(state.simulation);
        setSpeeches(state.speeches);
        setFlowArgs(state.flow_arguments);
        if (state.decision) setDecision(state.decision);
        setView("round");
      } else {
        localStorage.removeItem("dissio_active_round");
      }
    }).catch(() => {
      localStorage.removeItem("dissio_active_round");
    });
  }, [authState]);

  // ── State refresh ───────────────────────────────────────────────────────────

  const refreshState = useCallback(async (roundId: string) => {
    try {
      const state = await roundApi.getRoundState(roundId);
      setRoundState(state);
      setSimulation(state.simulation);
      setSpeeches(state.speeches);
      setFlowArgs(state.flow_arguments);
      if (state.decision) setDecision(state.decision);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        localStorage.removeItem("dissio_active_round");
        setView("setup");
        setSimulation(null);
      }
    }
  }, []);

  // ── Handlers ────────────────────────────────────────────────────────────────

  async function handleCreateRound(config: RoundSimulationConfig) {
    setLoading(true);
    setError(null);
    try {
      const sim = await roundApi.createRound(config);
      localStorage.setItem("dissio_active_round", sim.id);
      const started = await roundApi.startRound(sim.id);
      setSimulation(started);
      await refreshState(sim.id);
      setView("round");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to create round.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleSpeechSubmitted(speech: RoundSpeech) {
    setSpeeches((s) => [...s, speech]);
    if (simulation) await refreshState(simulation.id);
  }

  async function handleOpponentSpeechRequested() {
    if (!simulation || !roundState) return;
    setLoading(true);
    setError(null);
    try {
      const idempotencyKey = `opponent-${simulation.id}-${roundState.current_phase}`;
      const speech = await roundApi.generateOpponentSpeech(
        simulation.id,
        roundState.current_phase,
        idempotencyKey,
      );
      setSpeeches((s) => {
        const exists = s.some((x) => x.id === speech.id);
        return exists ? s : [...s, speech];
      });
      await refreshState(simulation.id);
      await handleAdvancePhase();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to generate opponent speech.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdvancePhase() {
    if (!simulation || !roundState) return;
    setLoading(true);
    try {
      const updated = await roundApi.advancePhase(simulation.id);
      setSimulation(updated);
      await refreshState(simulation.id);
    } catch (e) {
      // Phase advance can fail if already at final phase — not an error to surface
      if (e instanceof ApiError && e.status !== 400) {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateDecision() {
    if (!simulation) return;
    setLoading(true);
    setError(null);
    try {
      const d = await roundApi.generateDecision(simulation.id);
      setDecision(d);
      setView("ballot");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to generate decision.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleRejudge(judgeType: string) {
    if (!simulation) return;
    setLoading(true);
    setError(null);
    try {
      const d = await roundApi.rejudgeRound(simulation.id, judgeType);
      setDecision(d);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Rejudge failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateDrills() {
    if (!simulation) return;
    setLoading(true);
    try {
      const d = await roundApi.generateDrills(simulation.id);
      setDrills(d);
      setView("drills");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to generate drills.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleAbandonRound() {
    localStorage.removeItem("dissio_active_round");
    setSimulation(null);
    setRoundState(null);
    setSpeeches([]);
    setFlowArgs([]);
    setDecision(null);
    setDrills([]);
    setView("setup");
    setError(null);
  }

  // ── Loading / auth states ───────────────────────────────────────────────────

  if (authState === "loading") {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (authState === "signed-out") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center px-4 py-20">
        <h1 className="text-xl font-semibold">Sign in to practice a full round</h1>
        <p className="text-sm text-muted-foreground max-w-xs">
          Full-round simulation uses your saved evidence cards. Sign in to get started.
        </p>
        <button
          onClick={() => router.push("/login")}
          className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground"
        >
          Sign in
        </button>
      </div>
    );
  }

  const isCompleted =
    simulation?.status === "completed" ||
    simulation?.current_phase === "completed";

  // ── Setup view ──────────────────────────────────────────────────────────────

  if (view === "setup") {
    return (
      <div className="flex flex-col">
        <div className="py-8">
          <RoundSetupForm onStart={handleCreateRound} loading={loading} />
          {error && (
            <p className="text-xs text-red-600 text-center mt-4">{error}</p>
          )}
        </div>
      </div>
    );
  }

  if (!simulation || !roundState) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <p className="text-sm text-muted-foreground">Loading round...</p>
      </div>
    );
  }

  // ── Round view ──────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col">
      <RoundPhaseHeader
        phase={roundState.current_phase}
        phaseLabel={roundState.phase_label}
        studentSpeaksNow={roundState.student_speaks_now}
        studentSide={simulation.config.student_side}
        timeLimitSeconds={roundState.time_limit_seconds}
        phaseStartedAt={roundState.phase_started_at}
        status={simulation.status}
        coachingHint={
          simulation.config.coaching_hints_enabled
            ? roundState.coaching_hint
            : undefined
        }
      />

      {/* View tabs */}
      <div className="border-b px-4">
        <div className="flex gap-1 -mb-px">
          {(["round", "flow", "ballot", "drills"] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-4 py-2.5 text-sm border-b-2 transition-colors capitalize ${
                view === v
                  ? "border-primary text-primary font-medium"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {v}
            </button>
          ))}
          <button
            onClick={handleAbandonRound}
            className="ml-auto px-3 py-2.5 text-xs text-muted-foreground hover:text-red-500 transition-colors"
          >
            Exit round
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <div className="flex-1 p-4">
        {view === "round" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
            <div className="space-y-4">
              <h2 className="text-sm font-semibold">{roundState.phase_label}</h2>
              {isCompleted ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Round complete. Generate the final decision and post-round drills.
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={handleGenerateDecision}
                      disabled={loading}
                      className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                    >
                      {loading ? "Generating..." : "Generate Decision"}
                    </button>
                    {decision && (
                      <button
                        onClick={handleGenerateDrills}
                        disabled={loading}
                        className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
                      >
                        Generate Drills
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <RoundSpeechCapture
                  roundId={simulation.id}
                  phase={roundState.current_phase}
                  studentSide={simulation.config.student_side}
                  isStudentTurn={roundState.student_speaks_now}
                  onSpeechSubmitted={handleSpeechSubmitted}
                  onOpponentSpeechRequested={handleOpponentSpeechRequested}
                  onAdvancePhase={handleAdvancePhase}
                  isLoading={loading}
                />
              )}

              {speeches.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Speeches
                  </h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {speeches.slice(-3).map((s) => (
                      <div
                        key={s.id}
                        className="rounded-md border px-3 py-2 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium capitalize">
                            {s.phase.replace(/_/g, " ")}
                          </span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs ${
                              s.is_ai
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                                : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                            }`}
                          >
                            {s.is_ai ? "AI" : "You"}
                          </span>
                        </div>
                        {s.transcript && (
                          <p className="text-muted-foreground line-clamp-2">
                            {s.transcript.slice(0, 120)}...
                          </p>
                        )}
                        {s.legality_violations.length > 0 && (
                          <p className="text-amber-600 dark:text-amber-400">
                            ⚠ {s.legality_violations.length} legality issue(s)
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="hidden lg:block">
              <RoundFlow arguments={flowArgs} />
            </div>
          </div>
        )}

        {view === "flow" && <RoundFlow arguments={flowArgs} />}

        {view === "ballot" && (
          decision ? (
            <RoundBallotView
              decision={decision}
              allArguments={flowArgs}
              onRejudge={handleRejudge}
              isLoading={loading}
            />
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                No decision yet. Complete the round first.
              </p>
              {isCompleted && (
                <button
                  onClick={handleGenerateDecision}
                  disabled={loading}
                  className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                >
                  {loading ? "Generating..." : "Generate Decision"}
                </button>
              )}
            </div>
          )
        )}

        {view === "drills" && (
          <RoundDrillsView
            drills={drills}
            onGenerateDrills={handleGenerateDrills}
            isLoading={loading}
          />
        )}
      </div>
    </div>
  );
}
