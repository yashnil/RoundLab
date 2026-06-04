"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Mic, Plus, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import LogoutButton from "@/components/LogoutButton";

interface AppNavProps {
  /** Additional actions rendered before New Session / Sign Out */
  rightSlot?: React.ReactNode;
}

/* AppNav — 56px sticky bar, canvas background, single hairline bottom rule.
   Linear spec: top-nav height 56px, bg canvas, body-sm type. */
export default function AppNav({ rightSlot }: AppNavProps) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    // Load theme from localStorage on mount
    const savedTheme = localStorage.getItem("roundlab-theme") as "dark" | "light" | null;
    const initialTheme = savedTheme || "dark";
    setTheme(initialTheme);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(initialTheme);
  }, []);

  function toggleTheme() {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("roundlab-theme", newTheme);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(newTheme);
  }

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
          Individual
        </Link>
        <Link
          href="/team"
          className="hidden text-sm text-ink-subtle transition-colors hover:text-ink sm:block"
        >
          Team
        </Link>
        {rightSlot}

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="flex h-7 w-7 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        <Button asChild size="sm" className="h-7 gap-1.5 px-3 text-xs">
          <Link href="/session">
            <Plus size={12} />
            New Speech
          </Link>
        </Button>
        <LogoutButton />
      </div>
    </nav>
  );
}
