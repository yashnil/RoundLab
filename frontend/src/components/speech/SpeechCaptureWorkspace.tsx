"use client";

import { useEffect, type Dispatch, type SetStateAction, type ChangeEvent } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Mic, RefreshCw, Upload, FileText, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CardContent } from "@/components/ui/card";
import { T } from "@/lib/motion";
import { StepHeader, InlineAlert, WorkspaceCard } from "@/components/speech/reportPrimitives";
import { derivePasteStats, MIN_WORDS, PASTE_DELIVERY_LIMITATION } from "@/lib/practice/pasteText";
import CaptureSaveStatus from "@/components/practice/CaptureSaveStatus";
import { deriveCaptureStatus, shouldWarnBeforeLeaving } from "@/lib/practice/captureStatus";
import RecordingStudio, { type RecordState } from "@/components/RecordingStudio";
import UploadDropzone from "@/components/UploadDropzone";
import type { UseRecorder } from "@/hooks/useRecorder";
import type { UseSpeechUpload } from "@/hooks/useSpeechUpload";
import type { Speech } from "@/types";

type CaptureMode = "record" | "upload" | "paste";

export interface SpeechCaptureWorkspaceProps {
  speech: Speech;
  resetting: boolean;
  resetAudio: () => void;
  recBusy: boolean;
  mode: CaptureMode;
  setMode: Dispatch<SetStateAction<CaptureMode>>;
  recordStudioState: () => RecordState;
  rec: UseRecorder;
  handleStartRec: () => void;
  saveRec: () => void;
  handleDiscardRec: () => void;
  upload: UseSpeechUpload;
  onFileChange: (e: ChangeEvent<HTMLInputElement>) => void;
  uploadFile: () => void;
  pastedText: string;
  setPastedText: Dispatch<SetStateAction<string>>;
  pasteErr: string;
  submitPastedText: () => void;
  submittingText: boolean;
}

export default function SpeechCaptureWorkspace({
  speech, resetting, resetAudio, recBusy, mode, setMode, recordStudioState, rec,
  handleStartRec, saveRec, handleDiscardRec, upload, onFileChange, uploadFile,
  pastedText, setPastedText, pasteErr, submitPastedText, submittingText,
}: SpeechCaptureWorkspaceProps) {
  const captureStatus = deriveCaptureStatus({
    mode,
    recorderStatus: rec.state.status,
    uploadStatus: upload.status,
    hasSavedAudio: !!speech.audio_url,
    analysisActive: false,
    analysisFailed: false,
    pasteDirty: pastedText.trim().length > 0,
    submittingPaste: submittingText,
  });

  // Warn before leaving while a recording/file/draft isn't saved yet.
  useEffect(() => {
    if (!shouldWarnBeforeLeaving(captureStatus)) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [captureStatus]);

  return (
              <WorkspaceCard key="audio">
                <CardContent className="flex flex-col gap-4 px-5 py-5">
                  <StepHeader n={1} title="Audio" done={!!speech.audio_url} />
                  {captureStatus !== "empty" && captureStatus !== "saved" && (
                    <CaptureSaveStatus status={captureStatus} />
                  )}

                {speech.audio_url ? (
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-3 rounded-lg border border-ok/20 bg-ok/5 px-4 py-3">
                      <Mic size={13} className="shrink-0 text-ok" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-ok">Audio ready</p>
                        <p className="mt-0.5 truncate font-mono text-xs text-ok/50">
                          {speech.audio_url.split("/").pop()}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="secondary" size="sm" disabled={resetting} onClick={resetAudio}
                      className="w-fit gap-1.5 text-ink-faint hover:border-danger/30 hover:text-danger"
                    >
                      <RefreshCw size={11} className={resetting ? "animate-spin" : ""} />
                      {resetting ? "Resetting…" : "Delete audio & re-record"}
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    <div className="flex gap-0.5 rounded-lg border border-hairline bg-surface-2 p-0.5">
                      {(["record", "upload", "paste"] as const).map((m) => (
                        <button
                          key={m}
                          type="button"
                          disabled={recBusy}
                          onClick={() => setMode(m)}
                          className={[
                            "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40",
                            mode === m
                              ? "border border-hairline bg-surface-3 text-ink"
                              : "text-ink-subtle hover:text-ink-muted",
                          ].join(" ")}
                        >
                          {m === "record" ? <><Mic size={12} /> Record</> : m === "upload" ? <><Upload size={12} /> Upload</> : <><FileText size={12} /> Paste</>}
                        </button>
                      ))}
                    </div>

                    <AnimatePresence mode="wait">
                      {mode === "record" ? (
                        <motion.div key="record"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                        >
                          <RecordingStudio
                            recordState={recordStudioState()} recordingSeconds={Math.round(rec.state.durationMs / 1000)}
                            recordObjectUrl={rec.state.url} recordError={rec.state.error ?? ""}
                            level={rec.level}
                            onStartRecording={handleStartRec} onStopRecording={rec.stop}
                            onSaveRecording={saveRec}  onDiscardRecording={handleDiscardRec}
                          />
                        </motion.div>
                      ) : mode === "upload" ? (
                        <motion.div key="upload"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                        >
                          <UploadDropzone
                            selectedFile={upload.selectedFile} fileError={upload.fileError}
                            uploadError={upload.uploadError}    uploading={upload.uploading}
                            onFileChange={onFileChange} onUpload={uploadFile} onClearFile={upload.clearFile}
                          />
                        </motion.div>
                      ) : (
                        <motion.div key="paste"
                          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                          transition={T.fast}
                          className="flex flex-col gap-3"
                        >
                          <div className="flex flex-col gap-2">
                            <label htmlFor="paste-speech" className="text-xs font-medium text-ink-subtle">Paste your speech text</label>
                            <textarea
                              id="paste-speech"
                              value={pastedText}
                              onChange={(e) => setPastedText(e.target.value)}
                              placeholder={`Paste or type your speech here… (at least ${MIN_WORDS} words ≈ 30 seconds)`}
                              className="h-48 w-full rounded-md border border-hairline bg-surface-2 px-3 py-2 text-sm text-ink outline-none transition-colors focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20 resize-none"
                            />
                            {(() => {
                              const stats = derivePasteStats(pastedText);
                              if (stats.words === 0) {
                                return (
                                  <p className="text-xs text-ink-faint">
                                    Aim for at least {MIN_WORDS} words (~30 seconds of speaking).
                                  </p>
                                );
                              }
                              return (
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                                  <span className="tabular-nums text-ink-subtle">{stats.words} words</span>
                                  <span className="tabular-nums text-ink-faint">~{stats.speakingTime} speaking</span>
                                  {stats.meetsMinimum ? (
                                    <span className="text-ok">Ready to analyze</span>
                                  ) : (
                                    <span className="text-warn">
                                      {stats.wordsToMinimum} more word{stats.wordsToMinimum !== 1 ? "s" : ""} to the minimum
                                    </span>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                          {pasteErr && <InlineAlert variant="danger">{pasteErr}</InlineAlert>}
                          <Button
                            onClick={submitPastedText}
                            disabled={!pastedText.trim() || submittingText}
                            size="sm"
                            className="w-full"
                          >
                            {submittingText ? "Saving…" : "Save text & analyze"}
                          </Button>
                          <div className="flex items-start gap-2 rounded-lg border border-hairline bg-surface-2/60 px-3 py-2.5">
                            <Info size={12} className="mt-0.5 shrink-0 text-ink-faint" aria-hidden="true" />
                            <p className="text-xs leading-relaxed text-ink-subtle">{PASTE_DELIVERY_LIMITATION}</p>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
                </CardContent>
              </WorkspaceCard>
  );
}
