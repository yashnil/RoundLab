import { type ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
  badge?: string;
}

/**
 * SectionHeader — Consistent section titles across pages
 * Usage: <SectionHeader title="Recent Sessions" description="Your latest practice" />
 */
export default function SectionHeader({ title, description, action, badge }: SectionHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h2 className="text-title text-ink">{title}</h2>
          {badge && (
            <span className="rounded-full bg-lav/10 px-2 py-0.5 text-xs font-medium text-lav">
              {badge}
            </span>
          )}
        </div>
        {description && (
          <p className="mt-1 text-sm text-ink-subtle leading-relaxed">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
