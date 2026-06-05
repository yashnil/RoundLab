import { type LucideIcon, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion } from "motion/react";
import Link from "next/link";

interface ActionCardProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  stats?: { label: string; value: string | number }[];
  primaryAction: { label: string; href?: string; onClick?: () => void };
  secondaryAction?: { label: string; href?: string; onClick?: () => void };
  variant?: "default" | "featured";
  badge?: string;
}

/**
 * ActionCard — Large CTA card for hub pages
 * Usage: <ActionCard title="Individual Practice" description="..." primaryAction={{...}} />
 */
export default function ActionCard({
  title,
  description,
  icon: Icon,
  stats,
  primaryAction,
  secondaryAction,
  variant = "default",
  badge,
}: ActionCardProps) {
  const isFeatured = variant === "featured";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      className={`group relative overflow-hidden rounded-xl border p-6 transition-all ${
        isFeatured
          ? "border-lav/30 bg-gradient-to-br from-lav/5 to-lav/10 shadow-lg"
          : "border-hairline bg-surface-1 hover:border-hairline-strong"
      }`}
    >
      {/* Header */}
      <div className="flex items-start gap-4">
        {Icon && (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-lav/10">
            <Icon size={24} className="text-lav" />
          </div>
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-ink">{title}</h3>
            {badge && (
              <span className="rounded-full bg-lav/10 px-2 py-0.5 text-xs font-medium text-lav">
                {badge}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-ink-subtle leading-relaxed">{description}</p>
        </div>
      </div>

      {/* Stats */}
      {stats && stats.length > 0 && (
        <div className="mt-4 grid grid-cols-3 gap-3 border-t border-hairline pt-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <p className="text-xs text-ink-subtle">{stat.label}</p>
              <p className="mt-0.5 text-lg font-bold text-ink">{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-6 flex items-center gap-3">
        {primaryAction.href ? (
          <Button asChild size="lg" variant={isFeatured ? "default" : "secondary"}>
            <Link href={primaryAction.href}>
              {primaryAction.label}
              <ArrowRight size={16} />
            </Link>
          </Button>
        ) : (
          <Button size="lg" onClick={primaryAction.onClick} variant={isFeatured ? "default" : "secondary"}>
            {primaryAction.label}
            <ArrowRight size={16} />
          </Button>
        )}

        {secondaryAction && (
          secondaryAction.href ? (
            <Button asChild size="lg" variant="ghost">
              <Link href={secondaryAction.href}>
                {secondaryAction.label}
              </Link>
            </Button>
          ) : (
            <Button size="lg" variant="ghost" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )
        )}
      </div>

      {/* Decorative beam */}
      {isFeatured && <div className="beam-top" />}
    </motion.div>
  );
}
