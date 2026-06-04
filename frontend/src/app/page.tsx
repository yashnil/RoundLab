"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Mic, ArrowRight, Check, GitBranch, FileText, Zap, TrendingUp, BarChart3, Sun, Moon,
} from "lucide-react";
import { createClient } from "@/lib/supabase";
import { fadeUp, fadeUpInView, staggerParent, staggerChild, EASE } from "@/lib/motion";

// ── Product workspace preview ──────────────────────────────────────────────────

const PREVIEW_SCORES = [
  { label: "Clash",       value: 14, pct: 70 },
  { label: "Weighing",    value:  9, pct: 45 },
  { label: "Extensions",  value: 12, pct: 60 },
  { label: "Drops",       value: 16, pct: 80 },
  { label: "Judge Adapt.",value: 11, pct: 55 },
];

const PREVIEW_ARGS = [
  { type: "offense",  border: "border-l-ok",     label: "Economic burden shift",      claim: "Status quo tariffs impose $4.2T annual cost on developing nations." },
  { type: "weighing", border: "border-l-violet",  label: "Magnitude over reversibility",claim: "Prefer magnitude — irreversible structural poverty outweighs market disruption." },
  { type: "defense",  border: "border-l-blue",    label: "Federal solvency mechanism",  claim: "USFG uniquely positioned to coordinate cross-agency trade response." },
];

const TYPE_COLORS: Record<string, string> = {
  offense: "text-ok", weighing: "text-violet-hi", defense: "text-blue-hi",
};

function barColor(pct: number) {
  if (pct >= 70) return "bg-lav";
  if (pct >= 50) return "bg-warn";
  return "bg-danger";
}

function WorkspacePreview() {
  return (
    /* beam-top adds the animated top-edge sweep from globals.css */
    <div className="beam-top w-full overflow-hidden rounded-xl border border-hairline bg-surface-1">
      {/* Browser chrome */}
      <div className="flex items-center gap-1.5 border-b border-hairline bg-surface-2 px-4 py-3">
        <div className="h-2 w-2 rounded-full bg-hairline-strong" />
        <div className="h-2 w-2 rounded-full bg-hairline-strong" />
        <div className="h-2 w-2 rounded-full bg-hairline-strong" />
        <div className="mx-auto flex items-center gap-2 rounded-md border border-hairline bg-surface-3 px-3 py-1">
          <Mic size={9} className="text-lav" />
          <span className="text-xs text-ink-faint">roundlab.app/speech/1ac-state-r4</span>
        </div>
      </div>

      <div className="p-5">
        {/* Session header */}
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">1AC — State Championship · Round 4</p>
            <p className="mt-0.5 text-xs text-ink-subtle">Constructive · Pro · Flow judge</p>
          </div>
          <span className="rounded-full border border-ok/25 bg-ok/10 px-2 py-0.5 text-xs font-medium text-ok">
            Complete
          </span>
        </div>

        {/* Stepper */}
        <div className="mb-4 flex items-center gap-0">
          {["Audio", "Transcript", "Flow", "Feedback"].map((step, i) => (
            <div key={step} className="flex items-center">
              <span className="flex items-center gap-1 rounded-full bg-lav px-2 py-0.5 text-xs font-medium text-white">
                <Check size={8} strokeWidth={2.5} />{step}
              </span>
              {i < 3 && <div className="mx-1 h-px w-3 bg-hairline" />}
            </div>
          ))}
        </div>

        {/* Score */}
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-hairline bg-surface-2 px-4 py-3">
          <div className="flex h-11 w-11 shrink-0 flex-col items-center justify-center rounded-full border-2 border-lav">
            <span className="text-base font-bold leading-none text-ink">78</span>
            <span className="text-[9px] text-ink-faint">/100</span>
          </div>
          <div>
            <p className="text-xs font-semibold text-ink">Developing</p>
            <p className="mt-0.5 text-xs leading-snug text-ink-subtle">
              Strong warranting, but weighing needs explicit magnitude framing.
            </p>
          </div>
        </div>

        {/* Score bars — animate on mount */}
        <div className="mb-4 flex flex-col gap-2">
          {PREVIEW_SCORES.map(({ label, value, pct }, i) => (
            <div key={label} className="flex items-center gap-3">
              <span className="w-20 shrink-0 text-xs text-ink-subtle">{label}</span>
              <div className="h-1 flex-1 overflow-hidden rounded-full bg-hairline">
                <motion.div
                  className={`h-full rounded-full ${barColor(pct)}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.9, delay: 0.5 + i * 0.09, ease: EASE }}
                />
              </div>
              <span className="w-9 text-right text-xs text-ink-faint">{value}/20</span>
            </div>
          ))}
        </div>

        {/* Argument cards */}
        <div className="flex flex-col gap-2">
          {PREVIEW_ARGS.map((a, i) => (
            <motion.div
              key={a.label}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 1.1 + i * 0.1, ease: EASE }}
              className={`rounded-lg border border-l-4 border-hairline bg-surface-2 px-3 py-2 ${a.border}`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-semibold text-ink">{a.label}</p>
                <span className={`text-[10px] font-medium capitalize ${TYPE_COLORS[a.type]}`}>{a.type}</span>
              </div>
              <p className="mt-1 text-xs leading-snug text-ink-subtle">{a.claim}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

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

const WORKFLOW = [
  { icon: Mic,       n: "01", title: "Record your speech",       body: "Speak for 30+ seconds. Live mic or audio file. Works on any device." },
  { icon: GitBranch, n: "02", title: "Get your flow",            body: "Every argument mapped — claim, warrant, evidence, impact — automatically." },
  { icon: FileText,  n: "03", title: "Read your feedback",       body: "Ballot-style critique on clash, weighing, drops, and judge adaptation." },
  { icon: Zap,       n: "04", title: "Practice targeted drills", body: "Three drills targeting your specific weaknesses. Coaching, not case generation." },
];

const FEATURES = [
  { icon: BarChart3,   title: "Judge-native feedback",        body: "Every critique maps to a specific ballot dimension: clash, weighing, extensions, drops, or judge adaptation. No generic tips." },
  { icon: GitBranch,   title: "Structured argument mapping",  body: "Claim → warrant → evidence → impact. Extracted, scored by confidence, flagged for issues." },
  { icon: TrendingUp,  title: "PF-specific intelligence",     body: "Side-aware, speech-type-aware, judge-preference-aware. Built for Public Forum, not generic debate." },
];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [userLevel, setUserLevel] = useState<number | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

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
          setUserName(data.user.email || data.user.user_metadata?.name || null);

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
    setUserName(null);
    setUserLevel(null);
    router.push("/");
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <MarketingNav isLoggedIn={isLoggedIn} theme={theme} onThemeToggle={toggleTheme} onSignOut={handleSignOut} />

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section id="product" className="relative overflow-hidden">
        <div className="absolute inset-0 bg-dots opacity-40" />

        <div className="relative mx-auto max-w-5xl px-6 pb-16 pt-20">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1fr_1.2fr]">

            {/* Copy - Personalized for logged-in users */}
            <div className="flex flex-col gap-6">
              {isLoggedIn ? (
                <>
                  <motion.span
                    {...fadeUp(0)}
                    className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-lav"
                  >
                    {userLevel ? `Level ${userLevel}` : "Welcome back"}
                  </motion.span>

                  <motion.h1 {...fadeUp(0.07)} className="text-display text-ink">
                    Ready for your<br />next round?
                  </motion.h1>

                  <motion.p {...fadeUp(0.14)} className="max-w-sm text-base leading-relaxed text-ink-subtle">
                    {userName ? `Welcome back, ${userName.split('@')[0]}.` : "Welcome back."} Choose how you want to practice today.
                  </motion.p>

                  <motion.div {...fadeUp(0.2)} className="flex flex-wrap items-center gap-3">
                    <motion.a
                      href="/learn"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ duration: 0.12 }}
                      className="flex items-center gap-2 rounded-md bg-lav px-4 py-2.5 text-sm font-medium text-white hover:bg-lav-hi"
                    >
                      Start Learning <ArrowRight size={14} />
                    </motion.a>
                  </motion.div>
                </>
              ) : (
                <>
                  <motion.span
                    {...fadeUp(0)}
                    className="inline-block w-fit rounded-full border border-lav/30 bg-lav/10 px-3 py-1 text-eyebrow text-lav"
                  >
                    AI debate coach · Public Forum
                  </motion.span>

                  <motion.h1 {...fadeUp(0.07)} className="text-display text-ink">
                    Your AI<br />flow coach
                  </motion.h1>

                  <motion.p {...fadeUp(0.14)} className="max-w-sm text-base leading-relaxed text-ink-subtle">
                    Record a speech. Get structured argument analysis and ballot-style feedback in under a minute.
                    Built for novice and JV PF debaters who want to improve faster.
                  </motion.p>

                  <motion.div {...fadeUp(0.2)} className="flex flex-wrap items-center gap-3">
                    <motion.a
                      href="/login"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      transition={{ duration: 0.12 }}
                      className="flex items-center gap-2 rounded-md bg-lav px-4 py-2.5 text-sm font-medium text-white hover:bg-lav-hi"
                    >
                      Start for free <ArrowRight size={14} />
                    </motion.a>
                    <a href="#how"
                      className="rounded-md border border-hairline px-4 py-2.5 text-sm font-medium text-ink-muted transition-colors hover:border-hairline-strong hover:text-ink">
                      How it works
                    </a>
                  </motion.div>

                  <motion.div {...fadeUp(0.26)} className="flex items-center gap-4 pt-1">
                    {["30-second setup", "Judge-native", "PF-specific"].map((t) => (
                      <div key={t} className="flex items-center gap-1.5 text-xs text-ink-faint">
                        <Check size={10} className="text-ok" />{t}
                      </div>
                    ))}
                  </motion.div>
                </>
              )}
            </div>

            {/* Product panel */}
            <motion.div {...fadeUp(0.12)} className="w-full">
              <WorkspacePreview />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Metrics ─────────────────────────────────────────────────────── */}
      <section className="border-y border-hairline bg-surface-1">
        <div className="mx-auto grid max-w-4xl grid-cols-2 divide-x divide-hairline sm:grid-cols-4">
          {[
            { v: "30s",  l: "to get feedback"    },
            { v: "5",    l: "scoring dimensions" },
            { v: "PF",   l: "native intelligence" },
            { v: "100%", l: "argument-mapped"    },
          ].map(({ v, l }, i) => (
            <motion.div
              key={l}
              {...fadeUpInView(i * 0.06)}
              className="flex flex-col items-center gap-1 px-4 py-6 text-center"
            >
              <span className="text-title text-ink">{v}</span>
              <span className="text-xs text-ink-subtle">{l}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section id="how" className="mx-auto max-w-4xl px-6 py-20">
        <div className="mb-10 flex flex-col gap-2">
          <p className="text-eyebrow text-ink-subtle">How it works</p>
          <h2 className="text-headline text-ink">Four steps to better rounds</h2>
        </div>

        <motion.div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2"
          variants={staggerParent(0.07)}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-60px" }}
        >
          {WORKFLOW.map((s) => (
            <motion.div
              key={s.n}
              variants={staggerChild}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              className="flex gap-3 rounded-xl border border-hairline bg-surface-1 p-5 transition-colors hover:border-hairline-strong"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-lav/20 bg-lav/10">
                <s.icon size={14} className="text-lav" />
              </div>
              <div className="flex flex-col gap-1">
                <p className="text-sm font-semibold text-ink">
                  <span className="mr-1.5 font-mono text-xs text-lav">{s.n}</span>{s.title}
                </p>
                <p className="text-xs leading-relaxed text-ink-subtle">{s.body}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ── Features ────────────────────────────────────────────────────── */}
      <section id="features" className="border-t border-hairline bg-surface-1">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <div className="mb-10 flex flex-col gap-2">
            <p className="text-eyebrow text-ink-subtle">Features</p>
            <h2 className="text-headline text-ink">Built for competitive PF</h2>
          </div>

          <motion.div
            className="grid grid-cols-1 gap-3 sm:grid-cols-3"
            variants={staggerParent(0.07)}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-60px" }}
          >
            {FEATURES.map((f) => (
              <motion.div
                key={f.title}
                variants={staggerChild}
                whileHover={{ y: -2, transition: { duration: 0.15 } }}
                className="flex flex-col gap-3 rounded-xl border border-hairline bg-surface-2 p-5 transition-colors hover:border-hairline-strong"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-lav/20 bg-lav/10">
                  <f.icon size={14} className="text-lav" />
                </div>
                <p className="text-heading text-ink">{f.title}</p>
                <p className="text-sm leading-relaxed text-ink-subtle">{f.body}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Drills ──────────────────────────────────────────────────────── */}
      <section id="drills" className="mx-auto max-w-4xl px-6 py-20">
        <div className="mb-10 flex flex-col gap-2">
          <p className="text-eyebrow text-ink-subtle">Practice Drills</p>
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
            <p className="text-eyebrow text-ink-subtle">Roadmap</p>
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
      <section className="border-t border-hairline">
        <div className="mx-auto max-w-lg px-6 py-20 text-center">
          <motion.div
            {...fadeUpInView()}
            className="flex flex-col items-center gap-5"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-lav">
              <Mic size={18} className="text-white" />
            </div>
            <h2 className="text-headline text-ink">Start improving today</h2>
            <p className="max-w-xs text-sm leading-relaxed text-ink-subtle">
              Free to try. No coach required. Record your speech and get real feedback.
            </p>
            <motion.a
              href="/login"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              transition={{ duration: 0.12 }}
              className="flex items-center gap-2 rounded-md bg-lav px-5 py-3 text-sm font-medium text-white hover:bg-lav-hi"
            >
              Get started free <ArrowRight size={14} />
            </motion.a>
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
