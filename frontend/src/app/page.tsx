"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { Mic, ArrowRight, Check } from "lucide-react";
import { createClient } from "@/lib/supabase";
import { useTheme } from "@/hooks/useTheme";
import { fadeUp, fadeUpInView } from "@/lib/motion";
import { HOME_PROOF_POINTS, DIFFERENTIATOR_POINTS } from "@/lib/marketing";
import HeroDebateConsole from "@/components/HeroDebateConsole";
import MarketingNav from "@/components/marketing/MarketingNav";
import MarketingFooter from "@/components/marketing/MarketingFooter";
import WorkflowRail from "@/components/marketing/WorkflowRail";
import EvidenceProvenanceStrip from "@/components/marketing/EvidenceProvenanceStrip";
import TeamWorkflowStrip from "@/components/marketing/TeamWorkflowStrip";
import ProductProofTabs from "@/components/marketing/ProductProofTabs";

const PROOF_ACCENT: Record<string, string> = {
  lav: "text-lav",
  ink: "text-ink",
  cyan: "text-cyan",
  ok: "text-ok",
};

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
    const greeting =
      GREETINGS_WITH_NAME[Math.floor(Math.random() * GREETINGS_WITH_NAME.length)];
    return greeting(firstName);
  }
  return GREETINGS_WITHOUT_NAME[Math.floor(Math.random() * GREETINGS_WITHOUT_NAME.length)];
}

function SectionHead({
  stamp,
  title,
  blurb,
  align = "left",
  headingId,
}: {
  stamp: string;
  title: string;
  blurb?: string;
  align?: "left" | "center";
  headingId?: string;
}) {
  return (
    <motion.div
      {...fadeUpInView(0)}
      className={"mb-8 flex flex-col gap-2 " + (align === "center" ? "items-center text-center" : "")}
    >
      <p className="section-stamp text-ink-subtle">{stamp}</p>
      <h2 id={headingId} className="text-headline text-ink">{title}</h2>
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

export default function LandingPage() {
  const router = useRouter();
  const { theme, toggle } = useTheme();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userLevel, setUserLevel] = useState<number | null>(null);
  const [greeting, setGreeting] = useState<string>("");

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
      {/* Skip link — off-canvas until keyboard Tab; overlays UI when focused */}
      <a
        href="#main-content"
        className="absolute -left-[9999px] top-3 z-[100] rounded-md bg-lav px-3 py-2 text-sm font-medium text-white focus:left-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
      >
        Skip to content
      </a>

      <MarketingNav
        isLoggedIn={isLoggedIn}
        theme={theme}
        onThemeToggle={toggle}
        onSignOut={handleSignOut}
      />

      <main id="main-content" tabIndex={-1} className="focus-visible:outline-none">

        {/* ── Hero ──────────────────────────────────────────────────────── */}
        <section aria-labelledby="hero-heading" className="relative overflow-hidden">
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
                      <span className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-ink">
                        {userLevel ? `Level ${userLevel} · Welcome back` : "Welcome back"}
                      </span>
                      <h1
                        id="hero-heading"
                        className="text-[2.5rem] font-bold leading-[1.05] tracking-tight text-ink sm:text-[3.5rem]"
                      >
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
                        Start a practice speech <ArrowRight size={14} aria-hidden />
                      </Link>
                      <Link
                        href="/dashboard"
                        className="rounded-xl border border-hairline px-5 py-3 text-sm font-medium text-ink-subtle transition-colors hover:border-hairline-strong hover:text-ink"
                      >
                        Open dashboard
                      </Link>
                    </motion.div>
                  </>
                ) : (
                  <>
                    <motion.div {...fadeUp(0)} className="flex flex-col gap-5">
                      <span className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-ink">
                        AI flow coach · Public Forum debate
                      </span>

                      <h1 id="hero-heading" className="flex flex-col gap-1">
                        <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-ink sm:text-[4rem] lg:text-[4.5rem]">
                          Speak.
                        </span>
                        <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-lav sm:text-[4rem] lg:text-[4.5rem]">
                          Get flowed.
                        </span>
                        <span className="block text-[2.75rem] font-bold leading-[1.0] tracking-[-0.04em] text-ink/70 sm:text-[4rem] lg:text-[4.5rem]">
                          Drill what matters.
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
                        Start practicing <ArrowRight size={14} aria-hidden />
                      </Link>
                      <Link
                        href="/demo"
                        className="rounded-xl border border-hairline px-6 py-3.5 text-sm font-medium text-ink-subtle transition-colors hover:border-hairline-strong hover:text-ink"
                      >
                        See a real report
                      </Link>
                    </motion.div>

                    {/* Trust marks — text-ink-subtle for AA contrast */}
                    <motion.div
                      {...fadeUp(0.24)}
                      className="flex flex-wrap items-center gap-x-5 gap-y-2"
                    >
                      {["Free to start", "No coach required", "Coaching, not cheating"].map((t) => (
                        <div key={t} className="flex items-center gap-1.5 text-xs">
                          <Check size={10} className="shrink-0 text-ok" aria-hidden />
                          <span className="text-ink-subtle">{t}</span>
                        </div>
                      ))}
                    </motion.div>

                    {/* Judge type pills */}
                    <motion.div
                      {...fadeUp(0.3)}
                      className="flex flex-wrap items-center gap-2"
                      aria-label="Reads for judge types"
                    >
                      <span className="text-xs text-ink-subtle">Reads for:</span>
                      {["Lay judge", "Flow judge", "Tech judge", "Coach"].map((j) => (
                        <span
                          key={j}
                          className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-eyebrow text-ink-subtle"
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

        {/* ── Proof strip — real product facts ──────────────────────────── */}
        <section
          aria-label="Key product facts"
          className="border-y border-hairline bg-surface-1/70 backdrop-blur-sm"
        >
          <div className="mx-auto grid max-w-4xl grid-cols-2 divide-x divide-hairline sm:grid-cols-4">
            {HOME_PROOF_POINTS.map((p, i) => (
              <motion.div
                key={p.label}
                {...fadeUpInView(i * 0.06)}
                className="flex flex-col items-center gap-1 px-4 py-6 text-center"
              >
                <span className={`text-title tabular-nums ${PROOF_ACCENT[p.accent]}`}>
                  {p.value}
                </span>
                <span className="text-xs text-ink-subtle">{p.label}</span>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── How it works — the practice loop ─────────────────────────── */}
        <section
          id="how-it-works"
          aria-labelledby="how-it-works-heading"
          className="scroll-mt-16 mx-auto max-w-5xl px-6 py-16"
        >
          <SectionHead
            headingId="how-it-works-heading"
            stamp="The practice loop"
            title="Every rep runs the same loop"
            blurb="Speak, get flowed, read the ballot, drill the weak link, and re-record. One loop, automatic."
            align="center"
          />
          <motion.div {...fadeUpInView(0.06)}>
            <WorkflowRail />
          </motion.div>
        </section>

        {/* ── Product proof — tabbed showcase ───────────────────────────── */}
        <section
          id="product-proof"
          aria-labelledby="product-proof-heading"
          className="scroll-mt-16 border-t border-hairline bg-surface-1/40"
        >
          <div className="mx-auto max-w-6xl px-6 py-20">
            <SectionHead
              headingId="product-proof-heading"
              stamp="Product"
              title="See exactly where the chain breaks"
              blurb="A diagnostic board, a judge-specific ballot, and side-by-side improvement — all from one practice speech."
            />
            <motion.div {...fadeUpInView(0.06)}>
              <ProductProofTabs />
            </motion.div>
          </div>
        </section>

        {/* ── Why RoundLab is different ─────────────────────────────────── */}
        <section
          aria-labelledby="differentiators-heading"
          className="border-t border-hairline"
        >
          <div className="mx-auto max-w-5xl px-6 py-20">
            <SectionHead
              headingId="differentiators-heading"
              stamp="Why RoundLab"
              title="Built for debate, not for writing essays"
              blurb="Every design decision starts with how a judge reads a round — not how a student generates content."
              align="center"
            />
            <motion.ul
              {...fadeUpInView(0.06)}
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
              role="list"
            >
              {DIFFERENTIATOR_POINTS.map((point) => (
                <li
                  key={point.title}
                  className="rounded-xl border border-hairline bg-surface-1 p-5"
                >
                  <p className="mb-1.5 text-sm font-semibold text-ink">{point.title}</p>
                  <p className="text-sm leading-relaxed text-ink-subtle">{point.body}</p>
                </li>
              ))}
            </motion.ul>
          </div>
        </section>

        {/* ── Evidence — provenance trail ───────────────────────────────── */}
        <section
          id="evidence"
          aria-labelledby="evidence-heading"
          className="scroll-mt-16 border-t border-hairline bg-surface-1/40"
        >
          <div className="mx-auto max-w-6xl px-6 py-20">
            <SectionHead
              headingId="evidence-heading"
              stamp="Evidence"
              title="Research that keeps its receipts"
              blurb="Evidence Studio cuts read-aloud cards and preserves the exact source quote — with the AI tag and citation kept visibly separate."
            />
            <motion.div {...fadeUpInView(0.06)}>
              <p className="sr-only">
                Five-step evidence chain: claim inputs, source URL, exact quote extracted,
                AI-generated tag, and saved card with provenance.
              </p>
              <div aria-hidden="true">
                <EvidenceProvenanceStrip />
              </div>
            </motion.div>
          </div>
        </section>

        {/* ── For coaches — team workflow ───────────────────────────────── */}
        <section
          id="for-coaches"
          aria-labelledby="coaches-heading"
          className="scroll-mt-16 border-t border-hairline"
        >
          <div className="mx-auto max-w-6xl px-6 py-20">
            <SectionHead
              headingId="coaches-heading"
              stamp="For coaches"
              title="Built for the whole squad"
              blurb="Assign practice, review submissions fast, and turn a team-wide skill gap into the next assigned drill."
            />
            <motion.div {...fadeUpInView(0.06)}>
              <p className="sr-only">
                Coach workflow: assign speeches, review submissions, surface skill gaps, assign
                targeted drills.
              </p>
              <div aria-hidden="true">
                <TeamWorkflowStrip />
              </div>
            </motion.div>
          </div>
        </section>

        {/* ── Convert ───────────────────────────────────────────────────── */}
        <section
          aria-labelledby="cta-heading"
          className="border-t border-hairline bg-surface-1/50"
        >
          <div className="mx-auto max-w-lg px-6 py-20 text-center">
            <motion.div {...fadeUpInView()} className="flex flex-col items-center gap-5">
              <div
                className="flex h-12 w-12 items-center justify-center rounded-2xl bg-lav"
                style={{ boxShadow: "0 0 28px -4px oklch(0.510 0.156 278 / 0.55)" }}
                aria-hidden="true"
              >
                <Mic size={20} className="text-white" aria-hidden />
              </div>
              <h2 id="cta-heading" className="text-headline text-ink">
                Start your first practice rep
              </h2>
              <p className="max-w-xs text-sm leading-relaxed text-ink-subtle">
                Record a PF speech and get a flow, a judge-style ballot, and three drills in
                under a minute. Free to start, no coach required.
              </p>
              <Link
                href="/login"
                className="glow-lav flex items-center gap-2 rounded-md bg-lav px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-lav-hi focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50 focus-visible:ring-offset-2"
              >
                Start practicing <ArrowRight size={14} aria-hidden />
              </Link>
              <p className="text-xs text-ink-subtle">No credit card required</p>
            </motion.div>
          </div>
        </section>

      </main>

      <MarketingFooter />
    </div>
  );
}
