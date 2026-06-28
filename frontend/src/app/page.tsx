"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Mic, ArrowRight, Check } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { useTheme } from "@/hooks/useTheme";
import { fadeUp, fadeUpInView } from "@/lib/motion";
import { HOME_PROOF_POINTS } from "@/lib/marketing";
import PipelineShowcase from "@/components/PipelineShowcase";
import HeroDebateConsole from "@/components/HeroDebateConsole";
import MarketingNav from "@/components/marketing/MarketingNav";
import MarketingFooter from "@/components/marketing/MarketingFooter";
import EvidenceProvenanceStrip from "@/components/marketing/EvidenceProvenanceStrip";
import TeamWorkflowStrip from "@/components/marketing/TeamWorkflowStrip";
import TrustGrid from "@/components/marketing/TrustGrid";
import SpeechFlowSection from "@/components/marketing/SpeechFlowSection";
import JudgeLensSection from "@/components/marketing/JudgeLensSection";
import DebateProofSection from "@/components/marketing/DebateProofSection";
import { useInViewOnce } from "@/hooks/useInViewOnce";

const PROOF_ACCENT: Record<string, string> = {
  lav: "text-lav",
  ink: "text-ink",
  cyan: "text-cyan",
  ok: "text-ok",
};

// Practice-focused greetings for logged-in users
const GREETINGS_WITH_NAME = [
  (name: string) => `Ready for your next round, ${name}?`,
  (name: string) => `Pick up where you left off, ${name}.`,
  (name: string) => `Let's sharpen your skills, ${name}.`,
];

const GREETINGS_WITHOUT_NAME = [
  "What are we sharpening today?",
  "Let's make this speech cleaner.",
  "Back for another practice rep?",
  "Want to turn feedback into points?",
  "Let's build a stronger ballot story.",
  "Ready to level up your next speech?",
];

function pickGreeting(firstName: string | null): string {
  if (firstName && Math.random() < 0.5) {
    const greeting = GREETINGS_WITH_NAME[Math.floor(Math.random() * GREETINGS_WITH_NAME.length)];
    return greeting(firstName);
  }
  return GREETINGS_WITHOUT_NAME[Math.floor(Math.random() * GREETINGS_WITHOUT_NAME.length)];
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const router = useRouter();
  const { theme, toggle } = useTheme();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userLevel, setUserLevel] = useState<number | null>(null);
  const [greeting, setGreeting] = useState<string>("");

  // Viewport trigger — PipelineShowcase only starts once in view
  const [walkthroughRef, walkthroughStarted] = useInViewOnce<HTMLDivElement>({ threshold: 0.15 });

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => {
        if (data.user) {
          setIsLoggedIn(true);
          const metadata = data.user.user_metadata || {};
          const name = metadata.first_name || metadata.name?.split(" ")[0] || null;
          setGreeting(pickGreeting(name));
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/${data.user.id}/progress`)
            .then((res) => res.json())
            .then((progress) => setUserLevel(progress.level))
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    setIsLoggedIn(false);
    setUserLevel(null);
    setGreeting("");
    router.push("/");
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <MarketingNav
        isLoggedIn={isLoggedIn}
        theme={theme}
        onThemeToggle={toggle}
        onSignOut={handleSignOut}
      />

      {/* ── Hero — the full promise ─────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Coordinate grid texture — structural depth without dot noise */}
        <div
          className="absolute inset-0 bg-grid pointer-events-none"
          style={{ opacity: 0.10 }}
          aria-hidden
        />
        {/* Top hairline accent */}
        <div
          className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-lav/40 to-transparent"
          aria-hidden
        />
        {/* Radial glow — top-right, near the console */}
        <div
          className="pointer-events-none absolute right-0 top-0 h-[520px] w-[520px] opacity-50 blur-3xl"
          style={{
            background:
              "radial-gradient(ellipse at 90% 10%, oklch(0.510 0.156 278 / 0.14) 0%, transparent 65%)",
          }}
          aria-hidden
        />

        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-16 lg:pb-28 lg:pt-24">
          <div className="grid grid-cols-1 items-start gap-10 lg:grid-cols-[1fr_420px] lg:gap-10 xl:grid-cols-[1fr_520px] xl:gap-14">
            <div className="flex flex-col gap-8">
              {isLoggedIn ? (
                <>
                  <motion.div {...fadeUp(0)} className="flex flex-col gap-4">
                    <span className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-lav">
                      {userLevel ? `Level ${userLevel} · Welcome back` : "Welcome back"}
                    </span>
                    <h1 className="text-[2.5rem] font-bold leading-[1.05] tracking-tight text-ink sm:text-[3.5rem]">
                      {greeting}
                    </h1>
                    <p className="max-w-sm text-base leading-relaxed text-ink-subtle">
                      Choose how you want to practice today.
                    </p>
                  </motion.div>

                  <motion.div {...fadeUp(0.14)} className="flex flex-wrap items-center gap-3">
                    <Link
                      href="/session"
                      className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
                    >
                      Start a practice speech <ArrowRight size={14} aria-hidden />
                    </Link>
                    <Link
                      href="/dashboard"
                      className="rounded-xl border border-hairline px-5 py-3 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
                    >
                      Open dashboard
                    </Link>
                  </motion.div>
                </>
              ) : (
                <>
                  <motion.div {...fadeUp(0)} className="flex flex-col gap-5">
                    <span className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-lav">
                      AI flow coach · Public Forum debate
                    </span>

                    <h1 className="flex flex-col gap-0.5">
                      <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-ink sm:text-[4rem] lg:text-[4.5rem]">
                        Speak.
                      </span>
                      <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-lav sm:text-[4rem] lg:text-[4.5rem]">
                        Get flowed.
                      </span>
                      <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-ink-muted sm:text-[4rem] lg:text-[4.5rem]">
                        Drill what matters.
                      </span>
                    </h1>

                    <p className="max-w-md text-base leading-relaxed text-ink-subtle lg:text-lg">
                      Dissio turns a practice speech into a flow, a judge-style ballot, and
                      your next adjustment — in under a minute.
                    </p>
                  </motion.div>

                  <motion.div {...fadeUp(0.18)} className="flex flex-wrap items-center gap-3">
                    <Link
                      href="/login"
                      className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
                    >
                      Start practicing <ArrowRight size={14} aria-hidden />
                    </Link>
                    <Link
                      href="/demo"
                      className="rounded-xl border border-hairline px-6 py-3.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
                    >
                      See a real report
                    </Link>
                  </motion.div>

                  <motion.div {...fadeUp(0.24)} className="flex flex-wrap items-center gap-x-5 gap-y-2">
                    {["Free to start", "No coach required", "Coaching, not cheating"].map((t) => (
                      <div key={t} className="flex items-center gap-1.5 text-xs">
                        <Check size={10} className="shrink-0 text-ok" aria-hidden />
                        <span className="text-ink-subtle">{t}</span>
                      </div>
                    ))}
                  </motion.div>

                  <motion.div {...fadeUp(0.30)} className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-ink-subtle">Reads for:</span>
                    {["Lay judge", "Flow judge", "Tech judge", "Coach"].map((j) => (
                      <span
                        key={j}
                        className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-eyebrow font-medium text-ink-subtle"
                      >
                        {j}
                      </span>
                    ))}
                  </motion.div>
                </>
              )}
            </div>

            <HeroDebateConsole />
          </div>
        </div>
      </section>

      {/* ── Proof rail — grounded, not floating ─────────────────────────── */}
      <section className="border-y border-hairline bg-surface-1">
        <div className="mx-auto grid max-w-4xl grid-cols-1 divide-y divide-hairline sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          {HOME_PROOF_POINTS.map((p, i) => (
            <motion.div
              key={p.label}
              {...fadeUpInView(i * 0.06)}
              className="flex flex-col items-center gap-1 px-6 py-5 text-center"
            >
              <span className={`text-title tabular-nums ${PROOF_ACCENT[p.accent]}`}>{p.value}</span>
              <span className="text-xs text-ink-subtle">{p.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Pipeline — fast visual overview of the complete loop ─────────── */}
      <section id="practice" className="scroll-mt-16 border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <motion.div
            {...fadeUpInView(0)}
            className="mb-8 flex flex-col items-center gap-2 text-center"
          >
            <p className="section-stamp">Capture</p>
            <h2 className="text-headline text-ink">Watch a speech become a flow</h2>
            <p className="max-w-2xl text-sm leading-relaxed text-ink-subtle">
              Record, upload, or paste. Dissio transcribes, extracts
              claim–warrant–evidence–impact structure, and assembles the report automatically.
            </p>
          </motion.div>
          <motion.div
            {...fadeUpInView(0.08)}
            className="beam-top overflow-hidden rounded-2xl border border-hairline bg-surface-1/90 backdrop-blur-sm"
            style={{
              boxShadow:
                "0 0 60px -16px oklch(0.510 0.156 278 / 0.18)," +
                "0 0 0 1px oklch(0.510 0.156 278 / 0.06)",
            }}
          >
            <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex h-5 w-5 items-center justify-center rounded-md bg-lav">
                  <Mic size={10} className="text-white" aria-hidden />
                </div>
                <span className="text-xs font-semibold text-ink">1AC · State Championship R4</span>
              </div>
              <span className="rounded-full border border-ok/25 bg-ok/10 px-2 py-0.5 text-[10px] font-semibold text-ok">
                Analysis complete
              </span>
            </div>
            <div className="p-5" ref={walkthroughRef}>
              <PipelineShowcase autoPlay stageMs={2400} start={walkthroughStarted} />
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── A: Speech to flow — interactive transcript annotation ────────── */}
      <SpeechFlowSection />

      {/* ── B: Judge lens — same C1 argument, three judge perspectives ───── */}
      <JudgeLensSection />

      {/* ── C: Coaching story — decisive moment, drill, transformation ───── */}
      <DebateProofSection />

      {/* ── Evidence — provenance trail ─────────────────────────────────── */}
      <section id="evidence" className="scroll-mt-16 border-t border-hairline">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <motion.div {...fadeUpInView(0)} className="mb-8 flex flex-col gap-2">
            <p className="section-stamp">Evidence</p>
            <h2 className="text-headline text-ink">Research that keeps its receipts</h2>
            <p className="max-w-lg text-sm leading-relaxed text-ink-subtle">
              Evidence Studio cuts read-aloud cards and preserves the exact source quote — with
              the AI tag and citation kept visibly separate.
            </p>
          </motion.div>
          <motion.div {...fadeUpInView(0.06)}>
            <EvidenceProvenanceStrip />
          </motion.div>
        </div>
      </section>

      {/* ── Team — coach workflow ───────────────────────────────────────── */}
      <section id="team" className="scroll-mt-16 border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <motion.div {...fadeUpInView(0)} className="mb-8 flex flex-col gap-2">
            <p className="section-stamp">For coaches</p>
            <h2 className="text-headline text-ink">Built for the whole squad</h2>
            <p className="max-w-lg text-sm leading-relaxed text-ink-subtle">
              Assign practice, review submissions fast, and turn a team-wide skill gap into the
              next assigned drill.
            </p>
          </motion.div>
          <motion.div {...fadeUpInView(0.06)}>
            <TeamWorkflowStrip />
          </motion.div>
        </div>
      </section>

      {/* ── Trust — coaching, not cheating ──────────────────────────────── */}
      <section id="trust" className="scroll-mt-16 border-t border-hairline">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <motion.div {...fadeUpInView(0)} className="mb-8 flex flex-col gap-2">
            <p className="section-stamp">Trust</p>
            <h2 className="text-headline text-ink">Why students and coaches trust it</h2>
            <p className="max-w-lg text-sm leading-relaxed text-ink-subtle">
              Dissio is a coach, not a shortcut — and it&apos;s explicit about what&apos;s
              source, what&apos;s AI, and what it can&apos;t judge.
            </p>
          </motion.div>
          <motion.div {...fadeUpInView(0.06)}>
            <TrustGrid />
          </motion.div>
        </div>
      </section>

      {/* ── Final CTA — restrained, narrative complete ───────────────────── */}
      <section className="border-t border-hairline" aria-label="Call to action">
        <div className="mx-auto max-w-2xl px-6 py-24 text-center">
          <motion.div {...fadeUpInView()} className="flex flex-col items-center gap-6">
            <h2 className="text-headline text-ink max-w-xl">
              Your next speech should know what the last one missed.
            </h2>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link
                href="/login"
                className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
              >
                Start practicing <ArrowRight size={14} aria-hidden />
              </Link>
              <Link
                href="/demo"
                className="rounded-xl border border-hairline px-6 py-3.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
              >
                See a sample report
              </Link>
            </div>
            <p className="text-xs text-ink-faint">Free to start · No coach required</p>
          </motion.div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
