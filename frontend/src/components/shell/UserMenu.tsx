"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, User as UserIcon, Settings, ClipboardCheck } from "lucide-react";
import {
  DropdownMenuRoot,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { createClient } from "@/lib/supabase";

export default function UserMenu() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
    });
  }, []);

  async function handleSignOut() {
    setSigningOut(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const initial = (email?.[0] ?? "U").toUpperCase();

  return (
    <DropdownMenuRoot>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-full border border-hairline bg-surface-2 text-xs font-semibold text-ink transition-colors hover:border-hairline-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lav/50"
          aria-label="Account menu"
        >
          {email ? initial : <UserIcon size={15} aria-hidden="true" />}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <span className="block text-xs font-normal text-ink-subtle">Signed in as</span>
          <span className="block truncate text-sm font-medium text-ink">
            {email ?? "Your account"}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => router.push("/pilot")}>
          <ClipboardCheck size={15} aria-hidden="true" />
          Pilot &amp; feedback
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => router.push("/learn")}>
          <Settings size={15} aria-hidden="true" />
          Learn &amp; guides
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          disabled={signingOut}
          onSelect={(e) => {
            e.preventDefault();
            handleSignOut();
          }}
        >
          <LogOut size={15} aria-hidden="true" />
          {signingOut ? "Signing out…" : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenuRoot>
  );
}
