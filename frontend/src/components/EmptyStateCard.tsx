import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "motion/react";

interface EmptyStateCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
  preview?: React.ReactNode;
}

/**
 * EmptyStateCard — Friendly empty states with clear next actions
 * Usage: <EmptyStateCard icon={Mic} title="No speeches yet" description="..." actionLabel="Start" onAction={...} />
 */
export default function EmptyStateCard({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  preview,
}: EmptyStateCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center rounded-xl border border-hairline bg-surface-1 px-6 py-12 text-center"
    >
      {/* Icon */}
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-lav/10">
        <Icon size={24} className="text-lav" />
      </div>

      {/* Content */}
      <h3 className="text-lg font-semibold text-ink">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-ink-subtle leading-relaxed">{description}</p>

      {/* Preview */}
      {preview && <div className="mt-6 w-full max-w-md">{preview}</div>}

      {/* Action */}
      {actionLabel && (
        <Button
          size="lg"
          className="mt-6"
          onClick={onAction}
          {...(actionHref ? { asChild: true } : {})}
        >
          {actionHref ? <a href={actionHref}>{actionLabel}</a> : actionLabel}
        </Button>
      )}
    </motion.div>
  );
}
