"use client";

import type { Dispatch, SetStateAction } from "react";
import { Swords, ArrowRight, Target, RefreshCw, Pencil, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CardContent } from "@/components/ui/card";
import SpeechReportNav from "@/components/speech/SpeechReportNav";
import {
  StepHeader, Collapsible, InlineAlert, CoachDiagnosis, WorkspaceCard,
  FlowSummary, TopIssueCoachNote, FlowLensNote, ContextualHelp, isReportStale,
} from "@/components/speech/reportPrimitives";
import ScoreBreakdown from "@/components/ScoreBreakdown";
import FlowCanvas from "@/components/speech/FlowCanvas";
import DrillCard from "@/components/DrillCard";
import JudgeModeSelector, { type JudgeViewMode } from "@/components/JudgeModeSelector";
import DeliveryCoachPanel, { DeliveryCoachPanelEmpty } from "@/components/DeliveryCoachPanel";
import TournamentWorkoutPanel from "@/components/TournamentWorkoutPanel";
import BlockCoveragePanel from "@/components/BlockCoveragePanel";
import FeedbackRating from "@/components/FeedbackRating";
import ConfusionReport from "@/components/ConfusionReport";
import FlowEditPanel from "@/components/FlowEditPanel";
import EmptyStateCard from "@/components/EmptyStateCard";
import { deriveNextBestAction } from "@/lib/blockfileHelpers";
import { initEditArgs, isFlowCorrectedAndNeedsRegen } from "@/lib/flowEditHelpers";
import type {
  Speech, FeedbackReport, ArgumentMap, ArgumentItem, Drill, DrillStatus, Transcript,
  Workout, DeliveryMetrics, BlockCoverageResponse, EvidenceCheckResult, ClaimEvidenceCheck,
} from "@/types";

export interface SpeechReportWorkspaceProps {
  speech: Speech | null;
  feedback: FeedbackReport | null;
  argMap: ArgumentMap | null;
  drills: Drill[];
  transcript: Transcript | null;
  userId: string | null;
  speechId: string;
  analyzingUnified: boolean;
  genFb: boolean;
  genDrills: boolean;
  drillErr: string;
  updatingDrill: string | null;
  workout: Workout | null | undefined;
  freshResults: EvidenceCheckResult[];
  savedChecks: ClaimEvidenceCheck[];
  blockCoverage: BlockCoverageResponse | null | undefined;
  hasBlockEntries: boolean;
  deliveryLoaded: boolean;
  deliveryMetrics: DeliveryMetrics | null;
  judgeViewMode: JudgeViewMode;
  flowEditMode: boolean;
  editingArgs: ArgumentItem[];
  savingCorrection: boolean;
  correctionErr: string;
  regenErr: string;
  regenerating: boolean;
  setFeedbackRated: Dispatch<SetStateAction<boolean>>;
  setWorkout: Dispatch<SetStateAction<Workout | null | undefined>>;
  setBlockCoverage: Dispatch<SetStateAction<BlockCoverageResponse | null | undefined>>;
  setJudgeViewMode: Dispatch<SetStateAction<JudgeViewMode>>;
  setFlowEditMode: Dispatch<SetStateAction<boolean>>;
  setEditingArgs: Dispatch<SetStateAction<ArgumentItem[]>>;
  setCorrectionErr: Dispatch<SetStateAction<string>>;
  generateFeedback: () => void;
  generateDrills: () => void;
  updateDrillStatus: (drillId: string, status: DrillStatus) => void;
  saveFlowCorrection: (args: ArgumentItem[], notes?: string) => void;
  regenerateFromFlow: () => void;
  startNewAttempt: () => void;
}

export default function SpeechReportWorkspace({
  speech, feedback, argMap, drills, transcript, userId, speechId, analyzingUnified,
  genFb, genDrills, drillErr, updatingDrill, workout, freshResults, savedChecks,
  blockCoverage, hasBlockEntries, deliveryLoaded, deliveryMetrics, judgeViewMode,
  flowEditMode, editingArgs, savingCorrection, correctionErr, regenErr,
  regenerating, setFeedbackRated, setWorkout, setBlockCoverage, setJudgeViewMode,
  setFlowEditMode, setEditingArgs, setCorrectionErr, generateFeedback,
  generateDrills, updateDrillStatus, saveFlowCorrection, regenerateFromFlow, startNewAttempt,
}: SpeechReportWorkspaceProps) {
  return (
              <>
                <SpeechReportNav
                  flags={{
                    hasFeedback: !!feedback,
                    hasFlow: !!argMap,
                    hasDrills: drills.length > 0,
                    hasTranscript: !!transcript,
                  }}
                />
                {/* Feedback (Coaching Report) */}
                {feedback && (
                  <WorkspaceCard key="fb-done" glow>
                    <CardContent id="overview" className="flex flex-col gap-5 px-5 py-5 scroll-mt-20">
                      <StepHeader n={4} title="Coaching Report" done />

                      {/* Regenerate Banner - only show if report is stale */}
                      {isReportStale(feedback) && (
                        <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div className="flex flex-col gap-1">
                            <p className="text-sm font-medium text-lav">Update Available</p>
                            <p className="text-xs text-ink-muted leading-relaxed">
                              This report uses an older rubric. Regenerate to apply the latest recalibrated scoring.
                            </p>
                          </div>
                          <Button
                            size="sm"
                            variant="default"
                            onClick={generateFeedback}
                            disabled={genFb}
                            className="shrink-0"
                          >
                            {genFb ? "Regenerating..." : "Regenerate Report"}
                          </Button>
                        </div>
                      )}

                      {/* Coach annotation — below the top structured issue */}
                      <TopIssueCoachNote issues={feedback.raw_feedback?.structured_issues} />

                      {/* Priority Cards - Top 3 Issues */}
                      {feedback.raw_feedback?.top_3_priorities?.length ? (
                        <div className="flex flex-col gap-3">
                          <div className="section-stamp" style={{ color: "oklch(0.640 0.215 25 / 0.8)" }}>
                            <span className="h-1.5 w-1.5 rounded-full bg-danger flex-shrink-0" />
                            Round-Losing Issues
                          </div>
                          <div className="grid grid-cols-1 gap-2">
                            {feedback.raw_feedback.top_3_priorities.map((p, i) => (
                              <div key={i} className="flex items-start gap-3 rounded-xl border border-danger/25 bg-danger/6 px-4 py-3">
                                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white mt-0.5">
                                  {i + 1}
                                </span>
                                <p className="text-sm leading-relaxed text-ink">{p}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {/* Strengths & Weaknesses as Cards */}
                      {(feedback.strengths.length > 0 || feedback.weaknesses.length > 0) && (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                          {feedback.strengths.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-xl border border-ok/20 bg-ok/5 p-4">
                              <p className="text-sm font-semibold text-ok">✓ What Landed</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.strengths.map((s, i) => (
                                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-ok" />
                                    {s}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {feedback.weaknesses.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-xl border border-warn/25 bg-warn/5 p-4">
                              <p className="text-sm font-semibold text-warn">⚠ Fix Before Next Round</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.weaknesses.map((w, i) => (
                                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn" />
                                    {w}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Judge Ballot */}
                      <div id="ballot" className="flex flex-col gap-3 scroll-mt-20">
                        <div className="section-stamp" style={{ color: "oklch(0.510 0.156 278 / 0.8)" }}>
                          <span className="h-1.5 w-1.5 rounded-full bg-lav flex-shrink-0" />
                          Judge Ballot
                        </div>
                        <div id="skills" className="rounded-xl border border-hairline bg-surface-2 p-4 scroll-mt-20">
                          <ScoreBreakdown
                            scores={feedback.scores}
                            speechType={speech?.speech_type}
                            scoreExplanations={feedback.raw_feedback?.score_explanations}
                          />
                        </div>
                      </div>

                      {/* Contextual help — warranting */}
                      <ContextualHelp question="Why does warranting matter so much?">
                        A warrant is the logical mechanism that connects your claim to your evidence. Without it, a judge can simply say &ldquo;so what?&rdquo; and ignore your argument even if the evidence is strong. Flow judges in particular will drop unwarranted arguments — a claim needs a clear &ldquo;because&rdquo; before the evidence or it doesn&apos;t count.
                      </ContextualHelp>

                      {/* Coach Diagnosis Cards */}
                      {(feedback.raw_feedback?.dropped_or_undercovered_arguments?.length ||
                        feedback.raw_feedback?.warranting_diagnostics?.length ||
                        feedback.raw_feedback?.weighing_diagnostics?.length ||
                        feedback.raw_feedback?.evidence_diagnostics?.length) ? (
                        <div className="flex flex-col gap-3">
                          <div className="section-stamp">
                            <span className="h-1.5 w-1.5 rounded-full bg-ink-subtle flex-shrink-0" />
                            Coach Diagnosis
                          </div>

                          {/* Dropped arguments */}
                          {feedback.raw_feedback?.dropped_or_undercovered_arguments && feedback.raw_feedback.dropped_or_undercovered_arguments.length > 0 && (
                            <div className="flex flex-col gap-2 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3">
                              <p className="text-sm font-semibold text-danger">Drops / Undercovered</p>
                              <ul className="flex flex-col gap-1.5">
                                {feedback.raw_feedback.dropped_or_undercovered_arguments.map((item, i) => (
                                  <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink-muted">
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-danger/60" />
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <CoachDiagnosis
                            category="warranting"
                            label="Warranting"
                            items={feedback.raw_feedback?.warranting_diagnostics ?? []}
                          />
                          <CoachDiagnosis
                            category="weighing"
                            label="Impact Weighing"
                            items={feedback.raw_feedback?.weighing_diagnostics ?? []}
                          />
                          <CoachDiagnosis
                            category="evidence"
                            label="Evidence Use"
                            items={feedback.raw_feedback?.evidence_diagnostics ?? []}
                          />
                        </div>
                      ) : null}

                      {/* Decision Logic (RFD) */}
                      {feedback.raw_feedback?.decision_logic && (
                        <div className="flex flex-col gap-2 rounded-xl border border-lav/20 bg-lav/5 px-4 py-3">
                          <div className="section-stamp" style={{ color: "oklch(0.660 0.130 278)" }}>
                            <span className="h-1.5 w-1.5 rounded-full bg-lav flex-shrink-0" />
                            Reason For Decision (RFD)
                          </div>
                          <p className="text-sm leading-relaxed text-ink-muted">
                            {feedback.raw_feedback.decision_logic}
                          </p>
                        </div>
                      )}

                      {/* Judge Adaptation Notes */}
                      {feedback.raw_feedback?.judge_adaptation_notes && (
                        <div className="flex flex-col gap-2 rounded-xl border border-hairline bg-surface-2 px-4 py-3">
                          <p className="text-sm font-semibold text-ink">Judge Adaptation</p>
                          <p className="text-sm leading-relaxed text-ink-muted">
                            {feedback.raw_feedback.judge_adaptation_notes}
                          </p>
                        </div>
                      )}

                      {/* Action Checklist */}
                      {feedback.raw_feedback?.recommendations?.length ? (
                        <div className="flex flex-col gap-3 rounded-xl border border-lav/20 bg-lav/5 p-4">
                          <p className="text-sm font-semibold text-lav">Before You Re-Record</p>
                          <ul className="flex flex-col gap-2">
                            {feedback.raw_feedback.recommendations.map((r, i) => (
                              <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-ink">
                                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border border-lav/30 bg-surface-1 text-[8px] font-bold text-lav/50">
                                  {i + 1}
                                </span>
                                {r}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}

                      {/* Feedback Rating + Confusion Report */}
                      {userId && (
                        <div className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 px-4 py-3">
                          <FeedbackRating
                            speechId={speechId}
                            userId={userId}
                            initialRating={(feedback.helpful_rating as "helpful" | "somewhat" | "not_helpful" | null) ?? null}
                            onRated={() => setFeedbackRated(true)}
                          />
                          <ConfusionReport
                            targetType="speech_report"
                            targetId={feedback.id}
                            userId={userId}
                          />
                        </div>
                      )}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* ── Practice Hub — groups Delivery Coach, Workout, Block Coverage, Drills ── */}
                {feedback && !analyzingUnified && (
                  <div className="flex items-center gap-2 px-1 pt-1">
                    <Swords size={13} className="shrink-0 text-ink-faint" />
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-ink-faint">
                      Practice Hub
                    </p>
                  </div>
                )}

                {/* Next best action */}
                {feedback && !analyzingUnified && userId && (
                  (() => {
                    const action = deriveNextBestAction({
                      workout: workout ?? null,
                      drillsIncomplete: drills.filter(d => d.status === "assigned").length,
                      hasEvidenceRisk:
                        freshResults.some(r => r.support_level === "unsupported") ||
                        savedChecks.some(c => c.support_level === "unsupported"),
                      hasMissingBlocks: (blockCoverage?.missing_count ?? 0) > 0,
                      hasBlockEntries,
                      hasFeedback: true,
                      speechStatus: speech?.status,
                      speechId,
                    });
                    return (
                      <WorkspaceCard key="next-best-action">
                        <CardContent className="px-5 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex flex-col gap-0.5">
                              <p className="text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                                Next best action
                              </p>
                              <p className="text-sm font-semibold text-ink">{action.label}</p>
                              <p className="text-xs text-ink-subtle">{action.description}</p>
                            </div>
                            {action.href && (
                              <a
                                href={action.href}
                                className="shrink-0 flex items-center gap-1 rounded-lg border border-hairline bg-surface-2 px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-3 transition-colors"
                              >
                                Go <ArrowRight size={11} />
                              </a>
                            )}
                          </div>
                        </CardContent>
                      </WorkspaceCard>
                    );
                  })()
                )}

                {/* Delivery Coach Panel — visible after coaching report is done */}
                {feedback && !analyzingUnified && deliveryLoaded && (
                  <WorkspaceCard key="delivery-coach">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Delivery Coach" done={!!deliveryMetrics} aside={
                        deliveryMetrics?.delivery_score !== null && deliveryMetrics?.delivery_score !== undefined ? (
                          <Badge variant="indigo">{deliveryMetrics.delivery_score}/100 delivery</Badge>
                        ) : undefined
                      } />
                      {deliveryMetrics ? (
                        <DeliveryCoachPanel metrics={deliveryMetrics} />
                      ) : (
                        <DeliveryCoachPanelEmpty />
                      )}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Tournament Prep Workout */}
                {feedback && !analyzingUnified && userId && (
                  <WorkspaceCard key="workout">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Tournament Prep Workout" done={workout?.status === "completed"} />
                      <TournamentWorkoutPanel
                        speechId={speechId}
                        userId={userId}
                        workout={workout}
                        onWorkoutChange={setWorkout}
                        onStartReRecord={startNewAttempt}
                      />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Block Coverage */}
                {feedback && !analyzingUnified && userId && (
                  <WorkspaceCard key="block-coverage">
                    <CardContent id="block-coverage" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <StepHeader title="Block Coverage" done={!!blockCoverage && blockCoverage.covered_count === blockCoverage.checks.length && blockCoverage.checks.length > 0} />
                      <BlockCoveragePanel
                        speechId={speechId}
                        userId={userId}
                        coverage={blockCoverage}
                        hasBlockEntries={hasBlockEntries}
                        onCoverageChange={setBlockCoverage}
                      />
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Recommended Practice / Drills */}
                {drills.length > 0 ? (
                  <WorkspaceCard key="drills-done">
                    {/* id="drills" is the anchor target for ReportVerdictPanel and PracticeLoopCTA #drills hrefs */}
                    <CardContent id="drills" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <StepHeader
                        title="Recommended Practice"
                        done
                        aside={
                          <Badge variant="indigo">
                            {drills.filter((d) => d.status !== "assigned").length}/{drills.length} attempted
                          </Badge>
                        }
                      />
                      <div className="flex items-start gap-3 rounded-lg border border-lav/20 bg-lav/5 px-4 py-3">
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Complete drills to turn feedback into improvement</p>
                          <p className="text-xs text-ink-subtle">
                            Each drill targets a specific weakness from your feedback. Practice the exercise, then re-record your speech to track progress.
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        {drills.map((drill, i) => (
                          <DrillCard
                            key={drill.id}
                            drill={drill}
                            index={i}
                            onStatusChange={updateDrillStatus}
                            updatingId={updatingDrill}
                            userId={userId ?? undefined}
                          />
                        ))}
                      </div>

                      {/* Re-record CTA after drills */}
                      <div className="flex items-center gap-3 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">Ready to re-record?</p>
                          <p className="text-xs text-ink-subtle">Practice a few drills above, then start a fresh attempt to track your progress.</p>
                        </div>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={startNewAttempt}
                          className="shrink-0 gap-1.5 text-lav hover:border-lav/40"
                        >
                          <RefreshCw size={11} />
                          New Attempt
                        </Button>
                      </div>
                    </CardContent>
                  </WorkspaceCard>
                ) : feedback && (
                  <WorkspaceCard key="drills-empty">
                    <CardContent className="flex flex-col gap-4 px-5 py-5">
                      <StepHeader title="Recommended Practice" done={false} />
                      <EmptyStateCard
                        icon={Target}
                        title="No practice drills yet"
                        description="Generate personalized drills based on your feedback to target your weaknesses and improve faster."
                        actionLabel="Generate Practice Drills"
                        onAction={generateDrills}
                      />
                      {genDrills && <p className="text-xs text-center text-ink-faint">Generating drills...</p>}
                      {drillErr && <InlineAlert variant="danger">{drillErr}</InlineAlert>}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* Flow */}
                {argMap && (
                  <WorkspaceCard key="flow-done">
                    <CardContent id="flow" className="flex flex-col gap-4 px-5 py-5 scroll-mt-20">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <StepHeader n={3} title="Flow" done aside={
                          <div className="flex items-center gap-2">
                            {argMap.source_type === "user_corrected" && (
                              <Badge variant="indigo">Flow corrected</Badge>
                            )}
                            <Badge variant="indigo">
                              {argMap.arguments.length} arg{argMap.arguments.length !== 1 ? "s" : ""}
                            </Badge>
                          </div>
                        } />
                        <div className="flex items-center gap-2">
                          <JudgeModeSelector value={judgeViewMode} onChange={setJudgeViewMode} />
                          <button
                            type="button"
                            onClick={() => { setFlowEditMode(true); setEditingArgs(initEditArgs(argMap.arguments)); setCorrectionErr(""); }}
                            className="flex items-center gap-1 rounded-md border border-hairline px-2 py-1 text-xs text-ink-faint hover:text-ink-subtle hover:border-hairline-strong transition-colors"
                          >
                            <Pencil size={10} />
                            Edit
                          </button>
                        </div>
                      </div>

                      {flowEditMode ? (
                        <FlowEditPanel
                          initialArgs={editingArgs}
                          onSave={saveFlowCorrection}
                          onCancel={() => setFlowEditMode(false)}
                          saving={savingCorrection}
                          saveError={correctionErr}
                        />
                      ) : (
                        <>
                          {/* Flow Summary */}
                          <FlowSummary argMap={argMap} />

                          {/* Lens note */}
                          <FlowLensNote judgeMode={judgeViewMode} />

                          {/* Contextual help */}
                          <div className="flex flex-col gap-1.5">
                            <ContextualHelp question="What is a flow?">
                              A flow is a structured map of every argument in your speech. Debate judges — especially flow judges — track claim, warrant, evidence, and impact for each contention. If your flow is clean and extended correctly, you can win even on a thin evidence base.
                            </ContextualHelp>
                            <ContextualHelp question="What does the judge lens change?">
                              Lay judges care about persuasion, clarity, and which side sounds more confident. Flow judges track every argument and drop. Switching the lens shows you the most important weaknesses for each judge type — helping you prioritize your prep.
                            </ContextualHelp>
                          </div>

                          {argMap.arguments.length === 0 ? (
                            <p className="text-sm text-ink-faint">No arguments extracted.</p>
                          ) : (
                            <FlowCanvas
                              args={argMap.arguments}
                              judgeMode={judgeViewMode}
                              transcriptHref="#transcript"
                              drillsHref="#drills"
                            />
                          )}
                        </>
                      )}

                      {/* Regenerate coaching CTA */}
                      {isFlowCorrectedAndNeedsRegen(argMap, feedback) && !flowEditMode && (
                        <div className="rounded-lg border border-lav/20 bg-lav/5 px-4 py-3 flex flex-col gap-3">
                          <div className="flex flex-col gap-1">
                            <p className="text-sm font-semibold text-lav">Flow corrected — regenerate coaching</p>
                            <p className="text-xs text-ink-subtle leading-relaxed">
                              Your flow was edited. Regenerate to get updated feedback and drills based on the corrected arguments.
                            </p>
                          </div>
                          {regenErr && <p className="text-xs text-danger">{regenErr}</p>}
                          <Button
                            size="sm"
                            onClick={regenerateFromFlow}
                            disabled={regenerating}
                            className="w-fit"
                          >
                            {regenerating ? "Regenerating…" : "Regenerate coaching from corrected flow"}
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </WorkspaceCard>
                )}

                {/* View Speech Text - Collapsed (completed session)
                    TODO: Future feature - Annotated Speech Text
                    - Highlight claims, warrants, evidence, impacts inline
                    - Underline weak warrants
                    - Flag unsupported evidence
                    - Show strong/weak segments with color coding
                    - Useful for students who want to see exactly where their speech succeeded/failed
                */}
                {transcript && (
                  <WorkspaceCard key="input-details">
                    <CardContent className="flex flex-col gap-3 px-5 py-5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-2">
                          <FileText size={14} className="text-ink-subtle" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-ink">View Speech Text</p>
                          <p className="text-xs text-ink-faint">{transcript.word_count} words</p>
                        </div>
                      </div>
                      <Collapsible label="Show full transcript">
                        <div className="rounded-lg border border-hairline bg-surface-2 p-4">
                          <p className="text-sm leading-relaxed text-ink whitespace-pre-wrap">{transcript.text}</p>
                        </div>
                      </Collapsible>
                    </CardContent>
                  </WorkspaceCard>
                )}
              </>
  );
}
