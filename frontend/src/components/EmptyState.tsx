import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  Icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; href: string };
  hint?: string;
}

export default function EmptyState({ Icon, title, description, action, hint }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-5 rounded-xl border border-hairline bg-surface-1 px-6 py-14 text-center">
      <div
        className="flex h-14 w-14 items-center justify-center rounded-2xl border border-lav/20 bg-lav/10"
        style={{ boxShadow: "0 0 24px -6px oklch(0.510 0.156 278 / 0.25)" }}
      >
        <Icon size={22} className="text-lav" />
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-heading text-ink">{title}</p>
        <p className="max-w-xs text-sm leading-relaxed text-ink-subtle">{description}</p>
        {hint && (
          <p className="max-w-xs text-xs text-ink-faint">{hint}</p>
        )}
      </div>
      {action && (
        <Button asChild size="sm" className="mt-1">
          <Link href={action.href}>{action.label}</Link>
        </Button>
      )}
    </div>
  );
}
