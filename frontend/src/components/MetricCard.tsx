import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: number | string;
  Icon: LucideIcon;
  iconColor: string;
  iconBg: string;
  className?: string;
}

export default function MetricCard({
  label,
  value,
  Icon,
  iconColor,
  iconBg,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border border-hairline bg-surface-1 px-4 py-4 transition-colors hover:border-hairline-strong",
        className
      )}
    >
      <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", iconBg)}>
        <Icon size={14} className={iconColor} />
      </div>
      <div className="min-w-0">
        <p className="text-title leading-none text-ink">{value}</p>
        <p className="mt-1 truncate text-xs text-ink-subtle">{label}</p>
      </div>
    </div>
  );
}
