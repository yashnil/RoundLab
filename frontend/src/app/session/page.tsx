"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Settings2, Mic, GitBranch, FileText, ArrowRight } from "lucide-react";
import AppNav from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import { slideInLeft, slideInRight, staggerParent, staggerChild, EASE } from "@/lib/motion";
import type { Speech } from "@/types";

const selectCls =
  "h-8 w-full rounded-md border border-hairline bg-surface-2 px-3 py-1.5 " +
  "text-sm text-ink outline-none transition-colors " +
  "focus-visible:border-lav/50 focus-visible:ring-2 focus-visible:ring-lav/20 " +
  "disabled:opacity-40";

const HOW_STEPS = [
  { icon: Settings2, n: "01", title: "Configure",     body: "Set speech type, side, and judge to calibrate feedback." },
  { icon: Mic,       n: "02", title: "Record",        body: "Speak for 30+ seconds via mic or audio file." },
  { icon: GitBranch, n: "03", title: "Get your flow", body: "Every argument mapped: claim, warrant, evidence, impact." },
  { icon: FileText,  n: "04", title: "Read feedback", body: "Ballot-style critique on clash, weighing, drops, judge adapt." },
];

function FieldLabel({ label, hint, required }: { label: string; hint?: string; required?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-xs font-medium text-ink-subtle">
        {label}{required && <span className="ml-0.5 text-ink-faint" aria-hidden>*</span>}
      </label>
      {hint && <p className="text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}

export default function SessionPage() {
  const router = useRouter();
  const [userId,     setUserId]     = useState<string | null>(null);
  const [userLoading,setUserLoading]= useState(true);
  const [title,      setTitle]      = useState("");
  const [speechType, setSpeechType] = useState("constructive");
  const [side,       setSide]       = useState("");
  const [judgeType,  setJudgeType]  = useState("");
  const [topic,      setTopic]      = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error,      setError]      = useState("");

  useEffect(() => {
    createClient().auth.getUser().then(({ data }) => {
      if (!data.user) router.replace("/login");
      else setUserId(data.user.id);
    }).finally(() => setUserLoading(false));
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setError(""); setSubmitting(true);
    try {
      const s = await apiFetch<Speech>("/speeches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId, title,
          speech_type: speechType,
          side: side || null,
          judge_type: judgeType || null,
          topic: topic || null,
        }),
      });
      router.push(`/speech/${s.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-canvas">
        <div className="mx-auto max-w-5xl px-6 py-10">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[2fr_3fr] lg:gap-14">

            {/* Left: context */}
            <motion.div {...slideInLeft(0)} className="flex flex-col gap-6">
              <div className="flex flex-col gap-3">
                <Badge variant="indigo" className="w-fit">New Session</Badge>
                <h1 className="text-title text-ink">Create your coaching session</h1>
                <p className="text-sm leading-relaxed text-ink-subtle">
                  Tell RoundLab about your speech. More context means more precise judge-style feedback.
                </p>
              </div>

              {/* Step callouts */}
              <motion.div
                className="flex flex-col gap-3"
                variants={staggerParent(0.07, 0.1)}
                initial="hidden"
                animate={userLoading ? "hidden" : "show"}
              >
                {userLoading
                  ? Array.from({ length: 4 }).map((_, i) => (
                      <div key={i} className="flex gap-3">
                        <Skeleton className="h-7 w-7 shrink-0 rounded-lg" />
                        <div className="flex flex-1 flex-col gap-1.5 pt-0.5">
                          <Skeleton className="h-3.5 w-24" />
                          <Skeleton className="h-3 w-full" />
                        </div>
                      </div>
                    ))
                  : HOW_STEPS.map((s) => (
                      <motion.div key={s.n} variants={staggerChild} className="flex gap-3">
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-hairline bg-surface-2">
                          <s.icon size={12} className="text-ink-subtle" />
                        </div>
                        <div className="flex flex-col gap-0.5">
                          <p className="text-sm font-semibold text-ink">
                            <span className="mr-1.5 font-mono text-xs text-lav">{s.n}</span>
                            {s.title}
                          </p>
                          <p className="text-xs leading-relaxed text-ink-subtle">{s.body}</p>
                        </div>
                      </motion.div>
                    ))}
              </motion.div>

              <p className="hidden text-xs text-ink-faint lg:block">
                You&apos;ll record or upload audio after creating the session.
              </p>
            </motion.div>

            {/* Right: form */}
            <motion.div {...slideInRight(0.05)}>
              {userLoading ? (
                <Card>
                  <CardContent className="flex flex-col gap-4 px-5 py-5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div key={i} className="flex flex-col gap-1.5">
                        <Skeleton className="h-3 w-20" />
                        <Skeleton className="h-8 w-full rounded-md" />
                      </div>
                    ))}
                    <Skeleton className="mt-1 h-8 w-full rounded-md" />
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="px-5 py-5">
                    <form onSubmit={handleSubmit} className="flex flex-col gap-4">

                      <div className="flex flex-col gap-1.5">
                        <FieldLabel label="Session name" hint='e.g. "1AC — State Championship"' required />
                        <Input
                          required placeholder="e.g. 1AC Round 1 — State"
                          value={title} onChange={(e) => setTitle(e.target.value)}
                          disabled={submitting}
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <FieldLabel label="Speech type" hint="What part of the round?" required />
                        <select className={selectCls} value={speechType}
                          onChange={(e) => setSpeechType(e.target.value)} disabled={submitting}>
                          <option value="constructive">Constructive</option>
                          <option value="rebuttal">Rebuttal</option>
                          <option value="summary">Summary</option>
                          <option value="final_focus">Final Focus</option>
                          <option value="crossfire">Crossfire</option>
                        </select>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="flex flex-col gap-1.5">
                          <FieldLabel label="Side" hint="Affects framing" />
                          <select className={selectCls} value={side}
                            onChange={(e) => setSide(e.target.value)} disabled={submitting}>
                            <option value="">— not set —</option>
                            <option value="pro">Pro</option>
                            <option value="con">Con</option>
                          </select>
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <FieldLabel label="Judge type" hint="Adapts tone" />
                          <select className={selectCls} value={judgeType}
                            onChange={(e) => setJudgeType(e.target.value)} disabled={submitting}>
                            <option value="">— not set —</option>
                            <option value="lay">Lay</option>
                            <option value="flow">Flow</option>
                            <option value="tech">Tech</option>
                            <option value="coach">Coach</option>
                          </select>
                        </div>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <FieldLabel label="Resolution" hint='The PF topic, e.g. "Resolved: The USFG should…"' />
                        <Input
                          placeholder="Resolved: …"
                          value={topic} onChange={(e) => setTopic(e.target.value)}
                          disabled={submitting}
                        />
                      </div>

                      {error && (
                        <motion.p
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.2, ease: EASE }}
                          className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger"
                        >
                          {error}
                        </motion.p>
                      )}

                      <motion.div
                        className="mt-1"
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        transition={{ duration: 0.12 }}
                      >
                        <Button type="submit" disabled={submitting} className="w-full gap-2">
                          {submitting ? "Creating session…" : (
                            <><span>Create Session</span><ArrowRight size={13} /></>
                          )}
                        </Button>
                      </motion.div>
                    </form>
                  </CardContent>
                </Card>
              )}
            </motion.div>
          </div>
        </div>
      </main>
    </>
  );
}
