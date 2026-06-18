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
import ArgumentHealthMatrix from "@/components/ArgumentHealthMatrix";
import JudgeLensComparison from "@/components/JudgeLensComparison";
import MarketingNav from "@/components/marketing/MarketingNav";
import MarketingFooter from "@/components/marketing/MarketingFooter";
import WorkflowRail from "@/components/marketing/WorkflowRail";
import ImprovementLanes from "@/components/marketing/ImprovementLanes";
import EvidenceProvenanceStrip from "@/components/marketing/EvidenceProvenanceStrip";
import TeamWorkflowStrip from "@/components/marketing/TeamWorkflowStrip";
import TrustGrid from "@/components/marketing/TrustGrid";
import SupportedTodayGrid from "@/components/marketing/SupportedTodayGrid";
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

// ── Reusable section heading ─────────────────────────────────────────────────────

function SectionHead({
  stamp,
  title,
  blurb,
  align = "left",
}: {
  stamp: string;
  title: string;
  blurb?: string;
  align?: "left" | "center";
}) {
  return (
    <motion.div
      {...fadeUpInView(0)}
      className={
        "mb-8 flex flex-col gap-2 " +
        (align === "center" ? "items-center text-center" : "")
      }
    >
      <p className="section-stamp">{stamp}</p>
      <h2 className="text-headline text-ink">{title}</h2>
      {blurb && (
        <p
          className={
            "text-sm leading-relaxed text-ink-subtle " +
            (align === "center" ? "max-w-2xl" : "max-w-lg")
          }
        >
          {blurb}
        </p>
      )}
    </motion.div>
  );
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
        <div className="absolute inset-0 bg-dots opacity-20" aria-hidden />
        <div
          className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-lav/40 to-transparent"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute right-0 top-0 h-96 w-96 opacity-60 blur-3xl"
          style={{
            background:
              "radial-gradient(ellipse at 100% 0%, oklch(0.510 0.156 278 / 0.12) 0%, transparent 70%)",
          }}
          aria-hidden
        />

        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-16 lg:pb-28 lg:pt-24">
          <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-[1fr_1fr] lg:gap-16 xl:grid-cols-[1fr_480px]">
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
                      className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-lav-hi"
                    >
                      Start a practice speech <ArrowRight size={14} />
                    </Link>
                    <Link
                      href="/dashboard"
                      className="rounded-xl border border-hairline px-5 py-3 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink"
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

                    <h1 className="flex flex-col gap-1">
                      <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-ink sm:text-[4rem] lg:text-[4.5rem]">
                        Speak.
                      </span>
                      <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-lav sm:text-[4rem] lg:text-[4.5rem]">
                        Get flowed.
                      </span>
                      <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-ink/70 sm:text-[4rem] lg:text-[4.5rem]">
                        Drill what<br className="sm:hidden" /> matters.
                      </span>
                    </h1>

                    <p className="max-w-md text-base leading-relaxed text-ink-subtle lg:text-lg">
                      RoundLab turns a practice speech into a flow, a judge-style ballot, and
                      your next adjustment — in under a minute.
                    </p>
                  </motion.div>

                  <motion.div {...fadeUp(0.18)} className="flex flex-wrap items-center gap-3">
                    <Link
                      href="/login"
                      className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-lav-hi"
                    >
                      Start practicing <ArrowRight size={14} />
                    </Link>
                    <Link
                      href="/demo"
                      className="rounded-xl border border-hairline px-6 py-3.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink"
                    >
                      See a real report
                    </Link>
                  </motion.div>

                  <motion.div {...fadeUp(0.24)} className="flex flex-wrap items-center gap-x-5 gap-y-2">
                    {["Free to start", "No coach required", "Coaching, not cheating"].map((t) => (
                      <div key={t} className="flex items-center gap-1.5 text-xs">
                        <Check size={10} className="shrink-0 text-ok" aria-hidden />
                        <span className="text-ink-faint">{t}</span>
                      </div>
                    ))}
                  </motion.div>

                  <motion.div {...fadeUp(0.3)} className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-ink-faint">Reads for:</span>
                    {["Lay judge", "Flow judge", "Tech judge", "Coach"].map((j) => (
                      <span
                        key={j}
                        className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-[10px] font-medium text-ink-subtle"
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

      {/* ── Proof strip — real product facts only ───────────────────────── */}
      <section className="border-y border-hairline bg-surface-1/70 backdrop-blur-sm">
        <div className="mx-auto grid max-w-4xl grid-cols-2 divide-x divide-hairline sm:grid-cols-4">
          {HOME_PROOF_POINTS.map((p, i) => (
            <motion.div
              key={p.label}
              {...fadeUpInView(i * 0.06)}
              className="flex flex-col items-center gap-1 px-4 py-6 text-center"
            >
              <span className={`text-title tabular-nums ${PROOF_ACCENT[p.accent]}`}>{p.value}</span>
              <span className="text-xs text-ink-subtle">{p.label}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── The loop — connected story, distinct per step ───────────────── */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <SectionHead
          stamp="The practice loop"
          title="Every rep runs the same loop"
          blurb="Speak, get flowed, read the ballot, drill the weak link, and re-record. One loop, automatic."
          align="center"
        />
        <motion.div {...fadeUpInView(0.06)}>
          <WorkflowRail />
        </motion.div>
      </section>

      {/* ── Practice — capture + analysis ───────────────────────────────── */}
      <section id="practice" className="scroll-mt-16 border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="Capture"
            title="Watch a speech become a flow"
            blurb="Record, upload, or paste. RoundLab transcribes, extracts claim–warrant–evidence–impact structure, and assembles the report automatically."
            align="center"
          />
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

      {/* ── Flow — diagnostic board ─────────────────────────────────────── */}
      <section id="flow" className="scroll-mt-16 border-t border-hairline">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="Flow"
            title="See exactly where the chain breaks"
            blurb="A diagnostic board across every contention — strong links, weak warrants, and missing evidence, before a flow judge finds them."
          />
          <motion.div
            {...fadeUpInView(0.06)}
            className="rounded-2xl border border-hairline bg-surface-1 p-5"
          >
            <div className="mb-4 flex items-center justify-between">
              <p className="text-heading text-ink">Flow diagnostic board</p>
              <span className="text-[10px] text-ink-faint">● strong · ⚠ weak · ✗ missing</span>
            </div>
            <ArgumentHealthMatrix />
          </motion.div>
        </div>
      </section>

      {/* ── Judge lens — same speech, four readings ─────────────────────── */}
      <section id="judge" className="scroll-mt-16 border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="Judge lens"
            title="One speech, four judges"
            blurb="The lens reorders what matters and rewrites the feedback — lay, flow, tech, or coach. Not a swapped badge."
          />
          <motion.div
            {...fadeUpInView(0.06)}
            className="rounded-2xl border border-hairline bg-surface-1 p-5"
          >
            <JudgeLensComparison />
          </motion.div>
        </div>
      </section>

      {/* ── Improvement — before/after re-record ────────────────────────── */}
      <section id="improve" className="scroll-mt-16 border-t border-hairline">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <SectionHead
            stamp="Improve"
            title="Improvement you can point to"
            blurb="Re-record after a drill and RoundLab shows the new behavior — a named warrant, real weighing — not just a higher number."
          />
          <motion.div {...fadeUpInView(0.06)}>
            <ImprovementLanes />
          </motion.div>
        </div>
      </section>

      {/* ── Evidence — provenance trail ─────────────────────────────────── */}
      <section id="evidence" className="scroll-mt-16 border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="Evidence"
            title="Research that keeps its receipts"
            blurb="Evidence Studio cuts read-aloud cards and preserves the exact source quote — with the AI tag and citation kept visibly separate."
          />
          <motion.div {...fadeUpInView(0.06)}>
            <EvidenceProvenanceStrip />
          </motion.div>
        </div>
      </section>

      {/* ── Team — coach workflow ───────────────────────────────────────── */}
      <section id="team" className="scroll-mt-16 border-t border-hairline">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="For coaches"
            title="Built for the whole squad"
            blurb="Assign practice, review submissions fast, and turn a team-wide skill gap into the next assigned drill."
          />
          <motion.div {...fadeUpInView(0.06)}>
            <TeamWorkflowStrip />
          </motion.div>
        </div>
      </section>

      {/* ── Trust — coaching, not cheating ──────────────────────────────── */}
      <section id="trust" className="scroll-mt-16 border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="Trust"
            title="Why students and coaches trust it"
            blurb="RoundLab is a coach, not a shortcut — and it's explicit about what's source, what's AI, and what it can't judge."
          />
          <motion.div {...fadeUpInView(0.06)}>
            <TrustGrid />
          </motion.div>
        </div>
      </section>

      {/* ── Supported today — replaces the stale roadmap ────────────────── */}
      <section id="supported" className="scroll-mt-16 border-t border-hairline">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionHead
            stamp="Available now"
            title="What RoundLab supports today"
            blurb="Every capability below is live — tap any one to open it."
          />
          <motion.div {...fadeUpInView(0.06)}>
            <SupportedTodayGrid />
          </motion.div>
        </div>
      </section>

      {/* ── Convert ─────────────────────────────────────────────────────── */}
      <section className="border-t border-hairline bg-surface-1/50">
        <div className="mx-auto max-w-lg px-6 py-20 text-center">
          <motion.div {...fadeUpInView()} className="flex flex-col items-center gap-5">
            <div
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-lav"
              style={{ boxShadow: "0 0 28px -4px oklch(0.510 0.156 278 / 0.55)" }}
            >
              <Mic size={20} className="text-white" aria-hidden />
            </div>
            <h2 className="text-headline text-ink">Start your first practice rep</h2>
            <p className="max-w-xs text-sm leading-relaxed text-ink-subtle">
              Record a PF speech and get a flow, a judge-style ballot, and three drills in under a
              minute. Free to start, no coach required.
            </p>
            <Link
              href="/login"
              className="glow-lav flex items-center gap-2 rounded-md bg-lav px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-lav-hi"
            >
              Start practicing <ArrowRight size={14} />
            </Link>
            <p className="text-xs text-ink-faint">No credit card required</p>
          </motion.div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
