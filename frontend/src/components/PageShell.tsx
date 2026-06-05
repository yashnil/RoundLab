import { type ReactNode } from "react";
import AppNav from "@/components/AppNav";
import { motion } from "motion/react";

interface PageShellProps {
  children: ReactNode;
  maxWidth?: "full" | "7xl" | "5xl" | "3xl";
  rightSlot?: ReactNode;
}

/**
 * PageShell — Consistent page wrapper with nav and spacing
 * Usage: <PageShell><YourContent /></PageShell>
 */
export default function PageShell({ children, maxWidth = "7xl", rightSlot }: PageShellProps) {
  const maxWidthClasses = {
    full: "max-w-full",
    "7xl": "max-w-7xl",
    "5xl": "max-w-5xl",
    "3xl": "max-w-3xl",
  };

  return (
    <div className="min-h-screen bg-canvas">
      <AppNav rightSlot={rightSlot} />
      <motion.main
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`mx-auto px-4 py-8 sm:px-6 lg:px-8 ${maxWidthClasses[maxWidth]}`}
      >
        {children}
      </motion.main>
    </div>
  );
}
