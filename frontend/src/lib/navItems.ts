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
  GraduationCap,
  Users,
  ClipboardCheck,
  TrendingUp,
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
        match: ["/dashboard"],
        hint: "Your next step, progress, and recent rounds",
      },
      {
        href: "/session",
        label: "Practice",
        icon: Mic,
        match: ["/session", "/speech"],
        hint: "Record, upload, or paste a speech for analysis",
      },
      {
        href: "/progress",
        label: "Progress",
        icon: TrendingUp,
        match: ["/progress"],
        hint: "Skill trajectory, coverage, and your weekly plan",
      },
      {
        href: "/learn",
        label: "Drills & Learn",
        icon: GraduationCap,
        match: ["/learn", "/drills"],
        hint: "Targeted drills and skill-building guides",
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
        match: ["/team"],
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
