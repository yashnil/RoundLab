"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Mic,
  Upload,
  BookMarked,
  GraduationCap,
  Users,
  LayoutDashboard,
  Sun,
  Moon,
  ClipboardCheck,
  Swords,
  Scale,
  Flag,
  MessageSquarePlus,
  TrendingUp,
} from "lucide-react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from "@/components/ui/command";
import { getStoredTheme, toggleTheme } from "@/lib/theme";

/** Dispatch this event anywhere to open the command menu. */
export const OPEN_COMMAND_EVENT = "roundlab:open-command";

export function openCommandMenu() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(OPEN_COMMAND_EVENT));
  }
}

interface CommandAction {
  id: string;
  label: string;
  group: string;
  icon: React.ComponentType<{ size?: number }>;
  keywords?: string;
  shortcut?: string;
  run: () => void;
}

export default function CommandMenu() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const go = useCallback(
    (href: string) => () => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    function onOpenEvent() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_COMMAND_EVENT, onOpenEvent);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_COMMAND_EVENT, onOpenEvent);
    };
  }, []);

  const actions: CommandAction[] = [
    {
      id: "practice-constructive",
      label: "Start a Constructive",
      group: "Practice",
      icon: Mic,
      keywords: "record speech round constructive case contention build",
      run: go("/session?type=constructive"),
    },
    {
      id: "practice-rebuttal",
      label: "Start a Rebuttal",
      group: "Practice",
      icon: Swords,
      keywords: "record speech round rebuttal refute answer clash",
      run: go("/session?type=rebuttal"),
    },
    {
      id: "practice-summary",
      label: "Start a Summary",
      group: "Practice",
      icon: Scale,
      keywords: "record speech round summary collapse weigh narrow",
      run: go("/session?type=summary"),
    },
    {
      id: "practice-final-focus",
      label: "Start a Final Focus",
      group: "Practice",
      icon: Flag,
      keywords: "record speech round final focus voter crystallize",
      run: go("/session?type=final_focus"),
    },
    {
      id: "practice-upload",
      label: "Upload a speech",
      group: "Practice",
      icon: Upload,
      keywords: "upload audio file import",
      run: go("/session?mode=upload"),
    },
    {
      id: "nav-home",
      label: "Go to Home",
      group: "Go to",
      icon: LayoutDashboard,
      keywords: "dashboard home",
      run: go("/dashboard"),
    },
    {
      id: "nav-progress",
      label: "Open Progress",
      group: "Go to",
      icon: TrendingUp,
      keywords: "progress skills trajectory weekly plan development",
      run: go("/progress"),
    },
    {
      id: "nav-evidence",
      label: "Open Evidence Studio",
      group: "Go to",
      icon: BookMarked,
      keywords: "evidence research card cut sources",
      run: go("/evidence"),
    },
    {
      id: "nav-learn",
      label: "Open Learn & Drills",
      group: "Go to",
      icon: GraduationCap,
      keywords: "drills learn practice skills",
      run: go("/learn"),
    },
    {
      id: "nav-team",
      label: "Open Team workspace",
      group: "Go to",
      icon: Users,
      keywords: "team coach roster assignments",
      run: go("/team"),
    },
    {
      id: "nav-pilot",
      label: "Open Pilot & feedback",
      group: "Go to",
      icon: ClipboardCheck,
      keywords: "pilot feedback checklist",
      run: go("/pilot"),
    },
    {
      id: "toggle-theme",
      label: "Toggle light / dark theme",
      group: "Preferences",
      icon: getStoredTheme() === "dark" ? Sun : Moon,
      keywords: "theme dark light appearance",
      run: () => {
        toggleTheme(getStoredTheme());
        setOpen(false);
      },
    },
    {
      id: "send-feedback",
      label: "Send feedback",
      group: "Preferences",
      icon: MessageSquarePlus,
      keywords: "feedback report issue bug suggestion pilot",
      run: go("/pilot"),
    },
  ];

  const groups = Array.from(new Set(actions.map((a) => a.group)));

  return (
    <CommandDialog open={open} onOpenChange={setOpen} label="RoundLab command menu">
      <CommandInput placeholder="Search actions and destinations…" />
      <CommandList>
        <CommandEmpty>No matching actions.</CommandEmpty>
        {groups.map((group) => (
          <CommandGroup key={group} heading={group}>
            {actions
              .filter((a) => a.group === group)
              .map((a) => {
                const Icon = a.icon;
                return (
                  <CommandItem
                    key={a.id}
                    value={`${a.label} ${a.keywords ?? ""}`}
                    onSelect={a.run}
                  >
                    <Icon size={16} />
                    <span>{a.label}</span>
                    {a.shortcut && <CommandShortcut>{a.shortcut}</CommandShortcut>}
                  </CommandItem>
                );
              })}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
