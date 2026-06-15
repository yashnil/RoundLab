"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface RouteErrorProps {
  error: Error & { digest?: string };
  retry: () => void;
  /** Short, human title for what failed. */
  title?: string;
  /** One line on what the user can do / whether work was saved. */
  description?: string;
}

/**
 * Shared fallback UI for route-level error.tsx boundaries. Keeps messaging
 * honest (work-saved status + retry) and hides stack traces from users.
 */
export default function RouteError({
  error,
  retry,
  title = "This page didn’t load",
  description = "The problem is on our side, not your work. Try again, or head back home.",
}: RouteErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-6 py-16">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full border border-warn/30 bg-warn/10 text-warn">
          <AlertTriangle size={22} aria-hidden="true" />
        </div>
        <h1 className="text-title font-semibold text-ink">{title}</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-subtle">{description}</p>
        {error.digest && (
          <p className="mt-3 font-mono text-[0.6875rem] text-ink-faint">
            Reference: {error.digest}
          </p>
        )}
        <div className="mt-6 flex items-center justify-center gap-2">
          <Button onClick={retry} size="sm">
            <RotateCcw size={15} aria-hidden="true" />
            Try again
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard">
              <Home size={15} aria-hidden="true" />
              Go home
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
