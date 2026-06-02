import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  Icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; href: string };
}

export default function EmptyState({ Icon, title, description, action }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-hairline bg-surface-2">
          <Icon size={18} className="text-ink-subtle" />
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-heading text-ink">{title}</p>
          <p className="max-w-xs text-sm text-ink-subtle">{description}</p>
        </div>
        {action && (
          <Button asChild size="sm" className="mt-1">
            <Link href={action.href}>{action.label}</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
