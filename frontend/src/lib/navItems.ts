/**
 * Shared navigation model for RoundLab.
 *
 * - APP_NAV_ITEMS: flat list used by the public landing nav (unchanged contract).
 * - APP_NAV_GROUPS: grouped, icon-bearing model used by the authenticated
 *   sidebar (AppSidebar) and mobile navigation. Only wired to routes that exist.
 */

import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Mic,
  BookMarked,
  Library,
  GraduationCap,
  Users,
  ClipboardCheck,
  TrendingUp,
  Trophy,
  Scale,
  Swords,
} from "lucide-react";

export interface AppNavItem {
  href: string;
  label: string;
  /** Route prefixes that should mark this item active. */
  match: string[];
}

export const APP_NAV_ITEMS: AppNavItem[] = [
  { href: "/learn", label: "Learn", match: ["/learn"] },
  { href: "/dashboard", label: "Individual", match: ["/dashboard"] },
  { href: "/team", label: "Team", match: ["/team"] },
  { href: "/evidence", label: "Evidence", match: ["/evidence"] },
];

/** Is `item` active for the current `pathname`? Exact match or prefix match. */
export function isNavItemActive(
  item: { match: string[] },
  pathname: string | null | undefined,
): boolean {
  if (!pathname) return false;
  return item.match.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

// ── Practice loop step ─────────────────────────────────────────────────────

export type LoopStep = "practice" | "analyze" | "drill" | "improve";

/**
 * Maps the current pathname to the loop step it belongs to.
 * Returns null for routes outside the core loop (hub, research, team).
 *
 * Loop: Practice (/session, /speech) → Drill (/learn, /drills) → Improve (/progress)
 * "Analyze" is surfaced as a sidebar label only; the speech report is the practice step.
 */
export function deriveLoopStep(pathname: string | null | undefined): LoopStep | null {
  if (!pathname) return null;
  if (pathname.startsWith("/session") || pathname.startsWith("/speech")) return "practice";
  if (pathname.startsWith("/learn") || pathname.startsWith("/drills")) return "drill";
  if (pathname.startsWith("/progress")) return "improve";
  return null;
}

// ── Sidebar model ──────────────────────────────────────────────────────────

export interface SidebarNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  match: string[];
  /** Short description surfaced in tooltips / command menu. */
  hint?: string;
  /** Only render for users with coach access. */
  coachOnly?: boolean;
  /** Which step of the Practice→Analyze→Drill→Improve loop this item belongs to. */
  loopStep?: LoopStep;
}

export interface SidebarNavGroup {
  id: string;
  /** Group eyebrow label; null renders an unlabeled group. */
  label: string | null;
  items: SidebarNavItem[];
}

export const APP_NAV_GROUPS: SidebarNavGroup[] = [
  {
    id: "train",
    label: "Train",
    items: [
      {
        href: "/dashboard",
        label: "Home",
        icon: LayoutDashboard,
        match: ["/dashboard", "/missions"],
        hint: "Your next step, progress, and recent rounds",
      },
      {
        href: "/round-simulation",
        label: "Full Round",
        icon: Swords,
        match: ["/round-simulation"],
        hint: "Practice a full PF round against an evidence-constrained AI opponent",
        loopStep: "practice",
      },
      {
        href: "/session",
        label: "Practice",
        icon: Mic,
        match: ["/session", "/speech"],
        hint: "Record, upload, or paste a speech for analysis",
        loopStep: "practice",
      },
      {
        href: "/progress",
        label: "Progress",
        icon: TrendingUp,
        match: ["/progress"],
        hint: "Skill trajectory, coverage, and your weekly plan",
        loopStep: "improve",
      },
      {
        href: "/training",
        label: "Training",
        icon: GraduationCap,
        match: ["/training", "/diagnostic"],
        hint: "Personalized training plan and skill mastery tracker",
        loopStep: "improve",
      },
      {
        href: "/learn",
        label: "Drills & Learn",
        icon: GraduationCap,
        match: ["/learn", "/drills"],
        hint: "Targeted drills and skill-building guides",
        loopStep: "drill",
      },
    ],
  },
  {
    id: "research",
    label: "Research",
    items: [
      {
        href: "/evidence",
        label: "Evidence Studio",
        icon: BookMarked,
        match: ["/evidence"],
        hint: "Research sources and cut debate cards",
      },
      {
        href: "/library",
        label: "Library",
        icon: Library,
        match: ["/library"],
        hint: "Organized evidence by resolution and argument",
      },
      {
        href: "/prep",
        label: "Tournament Prep",
        icon: Trophy,
        match: ["/prep"],
        hint: "Readiness report, gap-driven workouts, and prep plan",
      },
      {
        href: "/judge-adaptation",
        label: "Judge Adaptation",
        icon: Scale,
        match: ["/judge-adaptation"],
        hint: "Adapt your material for lay, flow, technical, and coach judges",
      },
    ],
  },
  {
    id: "team",
    label: "Team",
    items: [
      {
        href: "/team",
        label: "Team",
        icon: Users,
        match: ["/team", "/team/assign", "/team/review", "/team/student"],
        hint: "Assignments, roster, and coach feedback",
      },
    ],
  },
  {
    id: "resources",
    label: "Resources",
    items: [
      {
        href: "/pilot",
        label: "Feedback",
        icon: ClipboardCheck,
        match: ["/pilot"],
        hint: "Practice-loop checklist and product feedback",
      },
    ],
  },
];

/** Flattened sidebar items, honoring coach access. */
export function flattenNavGroups(opts?: { isCoach?: boolean }): SidebarNavItem[] {
  const isCoach = opts?.isCoach ?? false;
  return APP_NAV_GROUPS.flatMap((g) => g.items).filter(
    (i) => !i.coachOnly || isCoach,
  );
}
