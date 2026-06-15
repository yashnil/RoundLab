import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  /** Small uppercase eyebrow label (debate-native section context). */
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  /** Right-aligned actions (buttons). */
  actions?: ReactNode;
  className?: string;
}

/**
 * PageHeader — consistent page title block used at the top of app routes.
 */
export default function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-1.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink-faint">
            {eyebrow}
          </p>
        )}
        <h1 className="text-title font-semibold text-ink">{title}</h1>
        {description && (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-subtle">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
