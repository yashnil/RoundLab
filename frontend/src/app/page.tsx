"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Mic, ArrowRight, Check, Zap, Sun, Moon,
} from "lucide-react";
import { createClient } from "@/lib/supabase";
import { fadeUp, fadeUpInView, staggerParent, staggerChild } from "@/lib/motion";
import PipelineShowcase from "@/components/PipelineShowcase";
import HeroDebateConsole from "@/components/HeroDebateConsole";
import ArgumentHealthMatrix from "@/components/ArgumentHealthMatrix";
import JudgeLensComparison from "@/components/JudgeLensComparison";
import RoundLabJourneyRail from "@/components/RoundLabJourneyRail";
import { useInViewOnce } from "@/hooks/useInViewOnce";

// ── Nav ────────────────────────────────────────────────────────────────────────

function MarketingNav({ isLoggedIn, theme, onThemeToggle, onSignOut }: {
  isLoggedIn: boolean;
  theme: "dark" | "light";
  onThemeToggle: () => void;
  onSignOut: () => void;
}) {
  return (
    <nav className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-hairline bg-canvas/95 px-5 backdrop-blur-md">
      <Link href="/" className="flex items-center gap-2 group">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-lav transition-colors group-hover:bg-lav-hi">
          <Mic size={12} className="text-white" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-ink">RoundLab</span>
      </Link>

      {/* Marketing nav for logged-out users */}
      {!isLoggedIn && (
        <div className="hidden items-center gap-5 sm:flex">
          <a href="#product"  className="text-sm text-ink-subtle transition-colors hover:text-ink">Product</a>
          <a href="#how"      className="text-sm text-ink-subtle transition-colors hover:text-ink">Workflow</a>
          <a href="#features" className="text-sm text-ink-subtle transition-colors hover:text-ink">Features</a>
          <a href="#drills"   className="text-sm text-ink-subtle transition-colors hover:text-ink">Drills</a>
          <a href="#roadmap"  className="text-sm text-ink-subtle transition-colors hover:text-ink">Roadmap</a>
        </div>
      )}

      {/* App nav for logged-in users */}
      {isLoggedIn && (
        <div className="hidden items-center gap-4 sm:flex">
          <Link href="/dashboard" className="text-sm text-ink-subtle transition-colors hover:text-ink">
            Individual
          </Link>
          <Link href="/team" className="text-sm text-ink-subtle transition-colors hover:text-ink">
            Team
          </Link>
        </div>
      )}

      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          onClick={onThemeToggle}
          className="flex h-7 w-7 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        {!isLoggedIn ? (
          <>
            <Link href="/login"
              className="rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink">
              Sign in
            </Link>
            <Link href="/login"
              className="rounded-md bg-lav px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-lav-hi">
              Get started
            </Link>
          </>
        ) : (
          <>
            <Link href="/session"
              className="rounded-md bg-lav px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-lav-hi">
              New Speech
            </Link>
            <button
              onClick={onSignOut}
              className="rounded-md border border-hairline bg-surface-1 px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink">
              Sign Out
            </button>
          </>
        )}
      </div>
    </nav>
  );
}

// ── Content data ───────────────────────────────────────────────────────────────

// Kept for type-safety; sections now render custom debate-native visuals inline.
const FEATURES = [
  { title: "Judge-style ballot feedback",  body: "Every critique maps to a ballot dimension: clash, weighing, extensions, drops, judge adaptation. Not generic tips." },
  { title: "Claim → Warrant → Impact",    body: "Every argument extracted and scored for confidence. Weak warrants and dropped arguments flagged instantly." },
  { title: "PF-native intelligence",      body: "Side-aware, speech-type-aware, judge-preference-aware. Built for Public Forum rounds, not generic debate." },
];

// ── Page ───────────────────────────────────────────────────────────────────────

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
  if (firstName) {
    // 50% chance to use name-based greeting
    if (Math.random() < 0.5) {
      const greeting = GREETINGS_WITH_NAME[Math.floor(Math.random() * GREETINGS_WITH_NAME.length)];
      return greeting(firstName);
    }
  }
  // Fall back to generic greeting
  return GREETINGS_WITHOUT_NAME[Math.floor(Math.random() * GREETINGS_WITHOUT_NAME.length)];
}

export default function LandingPage() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [firstName, setFirstName] = useState<string | null>(null);
  const [userLevel, setUserLevel] = useState<number | null>(null);
  const [greeting, setGreeting] = useState<string>("");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // Viewport trigger for walkthrough — PipelineShowcase only starts once in view
  const [walkthroughRef, walkthroughStarted] = useInViewOnce<HTMLDivElement>({ threshold: 0.15 });

  useEffect(() => {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem("roundlab-theme") as "dark" | "light" | null;
    const initialTheme = savedTheme || "dark";
    setTheme(initialTheme);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(initialTheme);

    // Check if user is logged in
    createClient().auth.getUser()
      .then(({ data }) => {
        if (data.user) {
          setIsLoggedIn(true);

          // Extract first name from metadata
          const metadata = data.user.user_metadata || {};
          const name = metadata.first_name || metadata.name?.split(' ')[0] || null;
          setFirstName(name);

          // Pick a greeting once per page load
          setGreeting(pickGreeting(name));

          // Fetch user progress for level
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/${data.user.id}/progress`)
            .then(res => res.json())
            .then(progress => {
              setUserLevel(progress.level);
            })
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  function toggleTheme() {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("roundlab-theme", newTheme);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(newTheme);
  }

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    setIsLoggedIn(false);
    setFirstName(null);
    setUserLevel(null);
    setGreeting("");
    router.push("/");
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <MarketingNav isLoggedIn={isLoggedIn} theme={theme} onThemeToggle={toggleTheme} onSignOut={handleSignOut} />

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section id="product" className="relative overflow-hidden">
        {/* Background texture */}
        <div className="absolute inset-0 bg-dots opacity-20" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-lav/40 to-transparent" />
        {/* Extra depth glow behind the pipeline */}
        <div className="pointer-events-none absolute right-0 top-0 h-96 w-96 opacity-60 blur-3xl"
          style={{ background: "radial-gradient(ellipse at 100% 0%, oklch(0.510 0.156 278 / 0.12) 0%, transparent 70%)" }} />

        <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-20 lg:pb-28 lg:pt-24">
          <div className="grid grid-cols-1 items-start gap-12 lg:grid-cols-[1fr_1fr] lg:gap-16 xl:grid-cols-[1fr_480px]">

            {/* ── Left: Copy ─────────────────────────────────────────── */}
            <div className="flex flex-col gap-8">
              {isLoggedIn ? (
                /* Logged-in: personalized greeting */
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
                    <motion.a
                      href="/learn"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ duration: 0.12 }}
                      className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-5 py-3 text-sm font-semibold text-white hover:bg-lav-hi"
                    >
                      Start Practice <ArrowRight size={14} />
                    </motion.a>
                    <Link href="/dashboard" className="rounded-xl border border-hairline px-5 py-3 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink">
                      Dashboard
                    </Link>
                  </motion.div>
                </>
              ) : (
                /* Logged-out: marketing hero */
                <>
                  <motion.div {...fadeUp(0)} className="flex flex-col gap-5">
                    {/* Eyebrow */}
                    <span className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-lav">
                      AI flow coach · Public Forum debate
                    </span>

                    {/* Cinematic headline */}
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

                    {/* Subtext */}
                    <p className="max-w-md text-base leading-relaxed text-ink-subtle lg:text-lg">
                      RoundLab turns a PF practice speech into a full debate analysis — flow, judge ballot, and personalized drills — in under a minute.
                    </p>
                  </motion.div>

                  {/* CTAs */}
                  <motion.div {...fadeUp(0.18)} className="flex flex-wrap items-center gap-3">
                    <motion.a
                      href="/login"
                      whileHover={{ scale: 1.02, y: -1 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ duration: 0.12 }}
                      className="glow-lav flex items-center gap-2 rounded-xl bg-lav px-6 py-3.5 text-sm font-semibold text-white hover:bg-lav-hi"
                    >
                      Start for free <ArrowRight size={14} />
                    </motion.a>
                    <a href="#how"
                      className="rounded-xl border border-hairline px-6 py-3.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink">
                      See how it works
                    </a>
                  </motion.div>

                  {/* Proof points */}
                  <motion.div {...fadeUp(0.24)} className="flex flex-wrap items-center gap-x-5 gap-y-2">
                    {[
                      { t: "Free to start",     color: "text-ok" },
                      { t: "No coach required", color: "text-ink-faint" },
                      { t: "PF-native AI",      color: "text-ink-faint" },
                    ].map(({ t, color }) => (
                      <div key={t} className="flex items-center gap-1.5 text-xs">
                        <Check size={10} className="text-ok shrink-0" />
                        <span className={color}>{t}</span>
                      </div>
                    ))}
                  </motion.div>

                  {/* Judge mode chips */}
                  <motion.div {...fadeUp(0.30)} className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-ink-faint">Works for:</span>
                    {["Lay judge", "Flow judge", "Tech judge", "Coach"].map((j) => (
                      <span key={j} className="rounded-full border border-hairline bg-surface-2 px-2.5 py-1 text-[10px] font-medium text-ink-subtle">
                        {j}
                      </span>
                    ))}
                  </motion.div>
                </>
              )}
            </div>

            {/* ── Right: Compact hero console ───────────────────────── */}
            <HeroDebateConsole />

          </div>
        </div>
      </section>

      {/* ── Metrics ─────────────────────────────────────────────────────── */}
      <section className="border-y border-hairline bg-surface-1/70 backdrop-blur-sm">
        <div className="mx-auto grid max-w-4xl grid-cols-2 divide-x divide-hairline sm:grid-cols-4">
          {[
            { v: "<30s", l: "to get feedback",     accent: "text-lav" },
            { v: "5",    l: "scoring dimensions",  accent: "text-ink" },
            { v: "PF",   l: "native intelligence", accent: "text-cyan" },
            { v: "3",    l: "drills per session",  accent: "text-ok"  },
          ].map(({ v, l, accent }, i) => (
            <motion.div
              key={l}
              {...fadeUpInView(i * 0.06)}
              className="flex flex-col items-center gap-1 px-4 py-6 text-center"
            >
              <span className={`text-title ${accent}`}>{v}</span>
              <span className="text-xs text-ink-subtle">{l}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Speech walkthrough ──────────────────────────────────────────── */}
      <section id="walkthrough" className="border-t border-hairline">
        <div className="mx-auto max-w-6xl px-6 py-20">

          {/* Section heading — centered */}
          <motion.div
            {...fadeUpInView(0)}
            className="mb-10 flex flex-col items-center gap-2 text-center"
          >
            <p className="section-stamp">In practice</p>
            <h2 className="text-headline text-ink">Watch a speech become a flow</h2>
            <p className="max-w-2xl text-sm leading-relaxed text-ink-subtle">
              RoundLab transcribes your speech, extracts claim-warrant-evidence-impact structure,
              writes a judge-style ballot, and turns the weakest link into a targeted drill.
            </p>
          </motion.div>

          {/* Full-width horizontal board */}
          <motion.div
            {...fadeUpInView(0.08)}
            className="beam-top overflow-hidden rounded-2xl border border-hairline bg-surface-1/90 backdrop-blur-sm"
            style={{
              boxShadow:
                "0 0 60px -16px oklch(0.510 0.156 278 / 0.18)," +
                "0 0 0 1px oklch(0.510 0.156 278 / 0.06)",
            }}
          >
            {/* Panel header */}
            <div className="flex items-center justify-between border-b border-hairline px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="flex h-5 w-5 items-center justify-center rounded-md bg-lav">
                  <Mic size={10} className="text-white" />
                </div>
                <span className="text-xs font-semibold text-ink">1AC · State Championship R4</span>
              </div>
              <span className="rounded-full border border-ok/25 bg-ok/10 px-2 py-0.5 text-[10px] font-semibold text-ok">
                Analysis complete
              </span>
            </div>

            {/* Horizontal pipeline board — starts only when scrolled into view */}
            <div className="p-5" ref={walkthroughRef}>
              <PipelineShowcase autoPlay stageMs={2400} start={walkthroughStarted} />
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Built like a coach ──────────────────────────────────────────── */}
      <section className="border-t border-hairline bg-surface-1/40">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <motion.div
            {...fadeUpInView(0)}
            className="mb-10 flex flex-col gap-2"
          >
            <p className="section-stamp">Under the hood</p>
            <h2 className="text-headline text-ink">Built like a coach, not a chatbot</h2>
            <p className="max-w-lg text-sm leading-relaxed text-ink-subtle">
              RoundLab understands debate structure — not just text. It finds the missing warrant before a flow judge does.
            </p>
          </motion.div>

          <div className="flex flex-col gap-5">
            {/* Argument health matrix — full width */}
            <motion.div
              {...fadeUpInView(0.06)}
              className="rounded-2xl border border-hairline bg-surface-1 p-5"
            >
              <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-heading text-ink">Flow diagnostic board</p>
                  <p className="mt-0.5 text-xs text-ink-subtle">
                    Where the argument chain breaks — across every contention.
                  </p>
                </div>
                <span className="text-[10px] text-ink-faint">● strong · ⚠ weak · ✗ missing</span>
              </div>
              <ArgumentHealthMatrix />
            </motion.div>

            {/* Judge lens comparison — full width */}
            <motion.div
              {...fadeUpInView(0.12)}
              className="rounded-2xl border border-hairline bg-surface-1 p-5"
            >
              <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-heading text-ink">Four judges, one speech</p>
                  <p className="mt-0.5 text-xs text-ink-subtle">
                    The same ballot reads differently depending on who&apos;s judging.
                  </p>
                </div>
                <span className="hidden text-[10px] text-ink-faint sm:block">
                  Lay · Flow · Tech · Coach
                </span>
              </div>
              <JudgeLensComparison />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section id="how" className="mx-auto max-w-4xl px-6 py-20">
        <div className="mb-8 flex flex-col gap-2">
          <span className="section-stamp">How it works</span>
          <h2 className="text-headline text-ink">Speech becomes debate intelligence</h2>
          <p className="max-w-md text-sm leading-relaxed text-ink-subtle">
            Every practice rep runs the same pipeline — automatically, in under a minute.
          </p>
        </div>

        {/* Practice loop rail — visual connector between steps */}
        <div className="mb-8 px-2">
          <RoundLabJourneyRail activeIndex={4} showLabels className="max-w-lg" />
        </div>

        <motion.div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4"
          variants={staggerParent(0.07)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-60px" }}
        >
          {/* Step 01 — Record */}
          <motion.div
            variants={staggerChild}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-1 p-5 transition-colors hover:border-hairline-strong"
          >
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-lav">01</span>
              <p className="text-heading text-ink">Record your speech</p>
            </div>
            <p className="text-xs leading-relaxed text-ink-subtle">
              Speak for 30+ seconds. Live mic or audio file. Works on any device.
            </p>
            {/* Mini waveform visual */}
            <div className="mt-1 flex items-end gap-0.5 overflow-hidden border-t border-hairline pt-3">
              {[4,8,14,10,18,12,16,9,13,7,15,11,6,17,8,12,10,15,9,13].map((h, i) => (
                <div
                  key={i}
                  className="w-1 shrink-0 rounded-full bg-lav"
                  style={{ height: `${h * 1.4}px`, minHeight: 2, opacity: 0.25 + (h / 20) * 0.6 }}
                />
              ))}
              <span className="ml-auto shrink-0 font-mono text-[10px] text-ink-faint">1:52</span>
            </div>
          </motion.div>

          {/* Step 02 — Flow */}
          <motion.div
            variants={staggerChild}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-1 p-5 transition-colors hover:border-hairline-strong"
          >
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-lav">02</span>
              <p className="text-heading text-ink">Get your flow</p>
            </div>
            <p className="text-xs leading-relaxed text-ink-subtle">
              Every argument mapped — claim, warrant, evidence, impact — automatically.
            </p>
            {/* Mini argument chain status strip */}
            <div className="mt-1 flex flex-col gap-2 border-t border-hairline pt-3">
              <div className="flex flex-wrap items-center gap-1">
                {[
                  { l: "Claim", ok: true },
                  { l: "Warrant", ok: true },
                  { l: "Evidence", ok: false, weak: true },
                  { l: "Impact", ok: true },
                ].map((node, i, arr) => (
                  <span key={node.l} className="flex items-center gap-1">
                    <span className={`h-1.5 w-1.5 rounded-full ${node.ok ? "bg-ok" : "bg-warn"}`} />
                    <span className={`text-[9px] font-semibold uppercase tracking-wider ${
                      node.ok ? "text-ink-faint" : "text-warn"
                    }`}>{node.l}</span>
                    {!node.ok && <span className="text-[9px] font-bold text-warn">⚠</span>}
                    {i < arr.length - 1 && <span className={`mx-0.5 h-px w-4 shrink-0 ${node.ok ? "bg-ok/35" : "bg-warn/30"}`} />}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-1.5 rounded-md border border-warn/20 bg-warn/5 px-2 py-1">
                <span className="h-1 w-1 rounded-full bg-warn" />
                <span className="text-[10px] text-warn">Weak evidence on C1 — citation unclear</span>
              </div>
            </div>
          </motion.div>

          {/* Step 03 — Feedback */}
          <motion.div
            variants={staggerChild}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-1 p-5 transition-colors hover:border-hairline-strong"
          >
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-lav">03</span>
              <p className="text-heading text-ink">Read your ballot</p>
            </div>
            <p className="text-xs leading-relaxed text-ink-subtle">
              Judge-style critique on clash, weighing, drops, and judge adaptation.
            </p>
            {/* Mini ballot score bars */}
            <div className="mt-1 flex flex-col gap-1.5 border-t border-hairline pt-3">
              {[
                { l: "Clash",    v: 14, max: 20 },
                { l: "Weighing", v:  9, max: 20, low: true },
                { l: "Coverage", v: 16, max: 20 },
              ].map((bar) => (
                <div key={bar.l} className="flex items-center gap-2">
                  <span className="w-16 shrink-0 text-[10px] text-ink-faint">{bar.l}</span>
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-hairline">
                    <div
                      className={`h-full rounded-full ${bar.low ? "bg-warn" : "bg-lav"}`}
                      style={{ width: `${(bar.v / bar.max) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 shrink-0 text-right text-[10px] tabular-nums text-ink-faint">
                    {bar.v}<span className="text-ink-faint/50">/{bar.max}</span>
                  </span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Step 04 — Drill */}
          <motion.div
            variants={staggerChild}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-1 p-5 transition-colors hover:border-hairline-strong"
          >
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-lav">04</span>
              <p className="text-heading text-ink">Practice targeted drills</p>
            </div>
            <p className="text-xs leading-relaxed text-ink-subtle">
              Three drills targeting your specific weaknesses. Coaching, not case generation.
            </p>
            {/* Mini drill card */}
            <div className="mt-1 flex flex-col gap-2 border-t border-hairline pt-3">
              <div className="flex items-start gap-2 rounded-lg border border-lav/20 bg-lav/8 px-3 py-2.5">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-lav">
                  <Zap size={10} className="text-white" />
                </div>
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <p className="text-[10px] font-semibold text-ink">Weighing Comparison Sprint</p>
                  <div className="flex items-center gap-1.5">
                    <span className="rounded-full border border-lav/25 bg-lav/10 px-1.5 py-0.5 text-[9px] font-medium text-lav">
                      Impact Weighing
                    </span>
                    <span className="text-[9px] text-ink-faint">90s · Intermediate</span>
                  </div>
                </div>
              </div>
              <p className="text-[10px] leading-relaxed text-ink-faint">
                Compare your impact against opponent offense using magnitude, probability, and timeframe.
              </p>
            </div>
          </motion.div>
        </motion.div>
      </section>

      {/* ── Features (bento layout) ──────────────────────────────────────── */}
      <section id="features" className="border-t border-hairline bg-surface-1">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <div className="mb-10 flex flex-col gap-2">
            <p className="section-stamp">Features</p>
            <h2 className="text-headline text-ink">Built for competitive PF</h2>
          </div>

          <motion.div
            className="grid grid-cols-1 gap-3 sm:grid-cols-6"
            variants={staggerParent(0.07)}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-60px" }}
          >
            {/* Large card — Ballot feedback with score visualization */}
            <motion.div
              variants={staggerChild}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              className="flex flex-col gap-4 rounded-xl border border-lav/20 bg-gradient-to-br from-lav/5 to-surface-2 p-5 transition-colors hover:border-lav/35 sm:col-span-4"
            >
              <div>
                <p className="text-heading text-ink">{FEATURES[0].title}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-subtle">{FEATURES[0].body}</p>
              </div>
              {/* Demo score bars */}
              <div className="rounded-lg border border-hairline bg-surface-1 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-eyebrow text-ink-faint">Judge ballot</span>
                  <span className="rounded-full border border-lav/25 bg-lav/10 px-2 py-0.5 text-[10px] font-semibold text-lav">78 / 100</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {[
                    { l: "Clash",            v: 14, max: 20 },
                    { l: "Weighing",         v:  9, max: 20, low: true },
                    { l: "Extensions",       v: 16, max: 20 },
                    { l: "Drops",            v: 18, max: 20 },
                    { l: "Judge Adaptation", v: 12, max: 20 },
                  ].map((bar) => (
                    <div key={bar.l} className="flex items-center gap-2">
                      <span className="w-24 shrink-0 text-[10px] text-ink-faint">{bar.l}</span>
                      <div className="h-1 flex-1 overflow-hidden rounded-full bg-hairline">
                        <div
                          className={`h-full rounded-full ${bar.low ? "bg-warn" : "bg-lav"}`}
                          style={{ width: `${(bar.v / bar.max) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 shrink-0 text-right text-[10px] tabular-nums text-ink-faint">{bar.v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

            {/* Small card — Argument chain */}
            <motion.div
              variants={staggerChild}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 p-5 transition-colors hover:border-hairline-strong sm:col-span-2"
            >
              <p className="text-heading text-ink">{FEATURES[1].title}</p>
              <p className="text-sm leading-relaxed text-ink-subtle">{FEATURES[1].body}</p>
              {/* Mini chain visual */}
              <div className="mt-auto flex flex-col gap-1.5 rounded-lg border border-hairline bg-surface-1 p-2.5">
                {[
                  { l: "Claim",    ok: true  },
                  { l: "Warrant",  ok: false },
                  { l: "Evidence", ok: true  },
                  { l: "Impact",   ok: true  },
                ].map((n) => (
                  <div key={n.l} className="flex items-center gap-2">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${n.ok ? "bg-ok" : "bg-danger"}`} />
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-ink-faint">{n.l}</span>
                    {!n.ok && <span className="ml-auto text-[9px] font-bold text-danger">✗ Missing</span>}
                    {n.ok  && <span className="ml-auto text-[9px] font-bold text-ok">✓</span>}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Full-width card — PF-native intelligence */}
            <motion.div
              variants={staggerChild}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 p-5 transition-colors hover:border-hairline-strong sm:col-span-6"
            >
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-heading text-ink">{FEATURES[2].title}</p>
                <div className="flex flex-wrap items-center gap-1.5">
                  {["Side-aware", "Speech-type-aware", "Judge-preference-aware"].map((tag) => (
                    <span key={tag} className="rounded-full border border-hairline bg-surface-1 px-2 py-0.5 text-[10px] text-ink-subtle">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-sm leading-relaxed text-ink-subtle">{FEATURES[2].body}</p>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ── Drills ──────────────────────────────────────────────────────── */}
      <section id="drills" className="mx-auto max-w-4xl px-6 py-20">
        <div className="mb-10 flex flex-col gap-2">
          <p className="section-stamp">Practice Drills</p>
          <h2 className="text-headline text-ink">Targeted coaching, not generic advice</h2>
        </div>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          {[
            {
              n: "01",
              title: "Grounded in your feedback",
              body: "Each drill maps directly to a weakness from your ballot — weighing gaps, dropped arguments, warrant failures.",
            },
            {
              n: "02",
              title: "PF-native exercises",
              body: "Impact comparison sprints, line-by-line response practice, extension drills. Debate-specific, not generic public speaking.",
            },
            {
              n: "03",
              title: "Track your progress",
              body: "Mark drills as attempted or completed. Then re-record your full speech with the same setup to measure improvement.",
            },
          ].map((card, i) => (
            <motion.div
              key={card.n}
              {...fadeUpInView(i * 0.07)}
              className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-1 p-5"
            >
              <span className="font-mono text-xs text-lav">{card.n}</span>
              <p className="text-heading text-ink">{card.title}</p>
              <p className="text-sm leading-relaxed text-ink-subtle">{card.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Roadmap ─────────────────────────────────────────────────────── */}
      <section id="roadmap" className="border-t border-hairline bg-surface-1">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <div className="mb-10 flex flex-col gap-2">
            <p className="section-stamp">Roadmap</p>
            <h2 className="text-headline text-ink">What&apos;s coming</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {[
              { label: "Now",  items: ["Record / upload speech", "AI argument flow", "Ballot-style feedback", "3 personalized drills"] },
              { label: "Next", items: ["Drill attempt recording", "Progress tracking over time", "Team dashboard", "Evidence upload & RAG"] },
            ].map(({ label, items }) => (
              <div key={label} className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 p-5">
                <p className="text-eyebrow text-lav">{label}</p>
                <ul className="flex flex-col gap-2">
                  {items.map((item) => (
                    <li key={item} className="flex items-center gap-2 text-sm text-ink-muted">
                      <span className="h-1 w-1 shrink-0 rounded-full bg-lav" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────────── */}
      <section className="border-t border-hairline bg-surface-1/50">
        <div className="mx-auto max-w-lg px-6 py-20 text-center">
          <motion.div
            {...fadeUpInView()}
            className="flex flex-col items-center gap-5"
          >
            <div
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-lav"
              style={{ boxShadow: "0 0 28px -4px oklch(0.510 0.156 278 / 0.55)" }}
            >
              <Mic size={20} className="text-white" />
            </div>
            <h2 className="text-headline text-ink">Start your first practice rep</h2>
            <p className="max-w-xs text-sm leading-relaxed text-ink-subtle">
              Free to start. No coach required. Record a PF speech and get judge-style feedback in under a minute.
            </p>
            <motion.a
              href="/login"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.12 }}
              className="glow-lav flex items-center gap-2 rounded-md bg-lav px-6 py-3 text-sm font-medium text-white hover:bg-lav-hi"
            >
              Get started free <ArrowRight size={14} />
            </motion.a>
            <p className="text-xs text-ink-faint">No credit card required</p>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-hairline">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-7">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-md bg-lav">
              <Mic size={10} className="text-white" />
            </div>
            <span className="text-xs font-medium text-ink-faint">RoundLab</span>
          </div>
          <p className="text-xs text-ink-faint">AI flow coach for Public Forum debaters</p>
        </div>
      </footer>
    </div>
  );
}
