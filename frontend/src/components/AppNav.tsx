"use client";

import Link from "next/link";
import { Mic, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import LogoutButton from "@/components/LogoutButton";

interface AppNavProps {
  /** Additional actions rendered before New Session / Sign Out */
  rightSlot?: React.ReactNode;
}

/* AppNav — 56px sticky bar, canvas background, single hairline bottom rule.
   Linear spec: top-nav height 56px, bg canvas, body-sm type. */
export default function AppNav({ rightSlot }: AppNavProps) {
  return (
    <nav className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-hairline bg-canvas px-5">
      {/* Brand */}
      <Link href="/" className="flex items-center gap-2 group">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-lav transition-colors group-hover:bg-lav-hi">
          <Mic size={12} className="text-white" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-ink">
          RoundLab
        </span>
      </Link>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Link
          href="/dashboard"
          className="hidden text-sm text-ink-subtle transition-colors hover:text-ink sm:block"
        >
          Dashboard
        </Link>
        <Link
          href="/team"
          className="hidden text-sm text-ink-subtle transition-colors hover:text-ink sm:block"
        >
          Team
        </Link>
        {rightSlot}
        <Button asChild size="sm" className="h-7 gap-1.5 px-3 text-xs">
          <Link href="/session">
            <Plus size={12} />
            New Session
          </Link>
        </Button>
        <LogoutButton />
      </div>
    </nav>
  );
}
