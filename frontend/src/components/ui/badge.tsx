import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-eyebrow font-medium leading-none",
  {
    variants: {
      variant: {
        /* ── Neutral ───────────────────────────────────────── */
        default:
          "border-hairline bg-surface-2 text-ink-subtle",

        /* ── Brand / active ───────────────────────────────── */
        indigo:
          "border-lav/25 bg-lav/10 text-lav-hi",

        /* ── Semantic ─────────────────────────────────────── */
        green:
          "border-ok/25 bg-ok/10 text-ok",
        amber:
          "border-warn/25 bg-warn/10 text-warn",
        red:
          "border-danger/25 bg-danger/10 text-danger",

        /* ── Argument type colors ─────────────────────────── */
        blue:
          "border-blue/25 bg-blue/10 text-blue-hi",
        violet:
          "border-violet/25 bg-violet/10 text-violet-hi",
        orange:
          "border-orange/25 bg-orange/10 text-orange-hi",

        /* ── Outline only ─────────────────────────────────── */
        outline:
          "border-hairline bg-transparent text-ink-subtle",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
