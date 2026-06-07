"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Mic, Plus, Sun, Moon } from "lucide-react";
import { motion } from "motion/react";
import { Button } from "@/components/ui/button";
import LogoutButton from "@/components/LogoutButton";
import { createClient } from "@/lib/supabase";

interface AppNavProps {
  /** Additional actions rendered before New Session / Sign Out */
  rightSlot?: React.ReactNode;
}

interface NavLinkProps {
  href: string;
  label: string;
  isActive: boolean;
}

function NavLink({ href, label, isActive }: NavLinkProps) {
  return (
    <Link
      href={href}
      className={`relative px-3 py-2 text-sm font-medium transition-colors ${
        isActive ? "text-ink" : "text-ink-subtle hover:text-ink"
      }`}
    >
      {label}
      {isActive && (
        <motion.div
          layoutId="nav-indicator"
          className="absolute bottom-0 left-0 right-0 h-0.5 bg-lav"
          transition={{ type: "spring", stiffness: 380, damping: 30 }}
        />
      )}
    </Link>
  );
}

/* AppNav — 56px sticky bar with route-aware navigation
   Shows different items based on auth state, highlights active route */
export default function AppNav({ rightSlot }: AppNavProps) {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Load theme from localStorage on mount
    const savedTheme = localStorage.getItem("roundlab-theme") as "dark" | "light" | null;
    const initialTheme = savedTheme || "dark";
    setTheme(initialTheme);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(initialTheme);

    // Check auth state
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsLoggedIn(!!session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsLoggedIn(!!session);
    });

    return () => subscription.unsubscribe();
  }, []);

  function toggleTheme() {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("roundlab-theme", newTheme);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(newTheme);
  }

  // Prevent hydration mismatch by not rendering auth-dependent content until mounted
  const showAuthContent = mounted && isLoggedIn;
  const showPublicContent = mounted && !isLoggedIn;

  return (
    <nav className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-hairline bg-canvas/95 backdrop-blur-md px-5" style={{ boxShadow: "0 1px 0 0 oklch(0.510 0.156 278 / 0.08)" }}>
      {/* Brand */}
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-lav transition-colors group-hover:bg-lav-hi">
            <Mic size={12} className="text-white" />
          </div>
          <span className="text-sm font-semibold tracking-tight text-ink">
            RoundLab
          </span>
        </Link>

        {/* Nav Links - Logged In */}
        {showAuthContent && (
          <div className="hidden items-center gap-1 md:flex">
            <NavLink href="/learn" label="Learn" isActive={pathname === "/learn"} />
            <NavLink href="/dashboard" label="Individual" isActive={pathname === "/dashboard"} />
            <NavLink href="/team" label="Team" isActive={pathname?.startsWith("/team") || false} />
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {rightSlot}

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-md text-ink-subtle transition-colors hover:bg-surface-2 hover:text-ink"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Logged In Actions */}
        {showAuthContent && (
          <>
            <Button asChild size="sm" className="h-8 gap-1.5 px-3 text-xs">
              <Link href="/session">
                <Plus size={14} />
                New Speech
              </Link>
            </Button>
            <LogoutButton />
          </>
        )}

        {/* Logged Out Actions */}
        {showPublicContent && (
          <>
            <Button asChild variant="ghost" size="sm" className="h-8 px-3 text-xs">
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild size="sm" className="h-8 px-3 text-xs">
              <Link href="/login">Get Started</Link>
            </Button>
          </>
        )}
      </div>
    </nav>
  );
}
