/**
 * Workspace layout — shared shell for every authenticated product route.
 *
 * AppShell (sidebar + header + mobile nav + command menu) is mounted once here
 * and stays alive across intra-workspace navigation. Individual pages render
 * inside <main> without re-mounting the chrome.
 *
 * Public routes (landing, login, auth, demo, share) live outside this group
 * and are unaffected.
 */
import AppShell from "@/components/shell/AppShell";
import { OfflineBanner } from "@/components/OfflineBanner";
import type { ReactNode } from "react";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return (
    <AppShell bare maxWidth="full">
      <OfflineBanner />
      {children}
    </AppShell>
  );
}
