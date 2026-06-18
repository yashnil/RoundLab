/**
 * Marketing presentation model for the public homepage.
 *
 * Why this lives in a pure module: the repo's jest setup only runs pure `.test.ts`
 * helpers (node env, no DOM). Keeping the homepage's link targets, proof facts, and
 * "supported today" capability list here lets `__tests__/marketing.test.ts` guard
 * against the two failure modes the audit called out:
 *   1. re-introducing a stale "roadmap / coming soon" claim for shipped features, and
 *   2. linking to routes/anchors that don't exist.
 *
 * Components import these arrays and render them; they own no copy of their own.
 */

// ── Routes that actually exist (mirrors frontend/src/app/**) ─────────────────────
// Prefixes — a target is valid if it equals or starts with one of these, or is an
// on-page anchor (`#…`). Keep in sync with the App Router tree.
export const EXISTING_ROUTE_PREFIXES = [
  "/",
  "/login",
  "/dashboard",
  "/session",
  "/speech",
  "/drills",
  "/team",
  "/evidence",
  "/learn",
  "/demo",
  "/pilot",
  "/share",
  "/evals",
] as const;

/** On-page section anchors the homepage defines. */
export const HOME_ANCHORS = [
  "#practice",
  "#flow",
  "#judge",
  "#improve",
  "#evidence",
  "#team",
  "#trust",
  "#supported",
] as const;

/** True for an on-page anchor or a link to a route that exists. */
export function isInternalTarget(href: string): boolean {
  if (href.startsWith("#")) {
    return (HOME_ANCHORS as readonly string[]).includes(href);
  }
  return EXISTING_ROUTE_PREFIXES.some(
    (p) => href === p || (p !== "/" && href.startsWith(p + "/")) || (p === "/" && href === "/"),
  );
}

/** Language that would signal a stale roadmap — banned from marketing copy. */
export const BANNED_ROADMAP_PHRASES = [
  "coming soon",
  "roadmap",
  "on the roadmap",
  "in the works",
  "future feature",
  "not yet available",
] as const;

export function hasBannedRoadmapLanguage(text: string): boolean {
  const t = text.toLowerCase();
  return BANNED_ROADMAP_PHRASES.some((p) => t.includes(p));
}

// ── Nav ──────────────────────────────────────────────────────────────────────────

export interface MarketingLink {
  label: string;
  href: string;
}

/** Logged-out marketing nav — short, anchors to capability acts (CTAs render separately). */
export const MARKETING_NAV_LINKS: MarketingLink[] = [
  { label: "Practice", href: "#practice" },
  { label: "Flow & ballot", href: "#flow" },
  { label: "Evidence", href: "#evidence" },
  { label: "For coaches", href: "#team" },
];

// ── Hero proof strip — defensible product facts only (no invented metrics) ───────

export interface ProofPoint {
  value: string;
  label: string;
  accent: "lav" | "ink" | "cyan" | "ok";
}

export const HOME_PROOF_POINTS: ProofPoint[] = [
  { value: "<60s", label: "speech to full report", accent: "lav" },
  { value: "5", label: "ballot scoring dimensions", accent: "ink" },
  { value: "4", label: "PF speech types covered", accent: "cyan" },
  { value: "3", label: "targeted drills per round", accent: "ok" },
];

// ── Interactive workflow rail — each step reveals something different ─────────────

export interface WorkflowStep {
  key: string;
  label: string;
  blurb: string;
}

export const WORKFLOW_STEPS: WorkflowStep[] = [
  { key: "speak", label: "Speak", blurb: "Record, upload, or paste a PF speech — any device." },
  { key: "flow", label: "Flow", blurb: "Claim · warrant · evidence · impact mapped per contention." },
  { key: "ballot", label: "Ballot", blurb: "Judge-style decision across clash, weighing, drops." },
  { key: "drill", label: "Drill", blurb: "Three reps aimed at your weakest link, not generic tips." },
  { key: "improve", label: "Improve", blurb: "Re-record and see exactly what changed." },
];

// ── Trust story — coaching, not cheating ──────────────────────────────────────────

export interface TrustPoint {
  title: string;
  body: string;
}

export const TRUST_POINTS: TrustPoint[] = [
  {
    title: "Coaching, not cheating",
    body: "RoundLab grades and drills your own speeches. It never writes your case or your cards for you.",
  },
  {
    title: "Evidence is never rewritten",
    body: "Source quotes are preserved exactly. AI proposes a tag and explanation — clearly marked as separate from the source.",
  },
  {
    title: "AI, user, and coach stay distinct",
    body: "Every report shows what the AI inferred, what you wrote, and what your coach added — never blended together.",
  },
  {
    title: "Your recordings stay yours",
    body: "Speeches are tied to your account. Coaches only see what you submit to an assignment.",
  },
  {
    title: "Honest about limits",
    body: "Delivery analysis needs audio; pasted text gets structure feedback only. The report says what it can and can't judge.",
  },
];

// ── Supported today (replaces the stale roadmap) ──────────────────────────────────

export interface SupportedCapability {
  title: string;
  body: string;
  href: string;
}

/** Every entry must link to a route/anchor that exists and describe a shipped feature. */
export const SUPPORTED_TODAY: SupportedCapability[] = [
  {
    title: "Record, upload, or paste",
    body: "Capture a speech live, drop in an audio file, or paste a transcript.",
    href: "/session",
  },
  {
    title: "Argument flow + judge ballot",
    body: "Per-contention flow and a five-dimension ballot, in one report.",
    href: "/demo",
  },
  {
    title: "Targeted drills",
    body: "Drills generated from your ballot's weakest dimension.",
    href: "/learn",
  },
  {
    title: "Progress over time",
    body: "Skill trends and re-record comparisons across your practice history.",
    href: "/dashboard",
  },
  {
    title: "Evidence Studio",
    body: "Research sources and cut read-aloud cards with provenance preserved.",
    href: "/evidence",
  },
  {
    title: "Team & coach tools",
    body: "Assignments, a review queue, and shared resolution context.",
    href: "/team",
  },
];

/** Small, honest note about active exploration. Deliberately not framed as a roadmap. */
export const CURRENTLY_EXPLORING =
  "We're actively refining the analysis pipeline and evidence tooling based on pilot feedback.";
