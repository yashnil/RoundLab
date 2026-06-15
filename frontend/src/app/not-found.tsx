import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-6">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full border border-hairline-strong bg-surface-2 text-ink-subtle">
          <Compass size={22} aria-hidden="true" />
        </div>
        <p className="text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink-faint">
          404
        </p>
        <h1 className="mt-1 text-title font-semibold text-ink">Page not found</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-subtle">
          The page you’re looking for doesn’t exist or may have moved. Let’s get you
          back to your practice.
        </p>
        <div className="mt-6 flex items-center justify-center gap-2">
          <Button asChild size="sm">
            <Link href="/dashboard">Go to Home</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/session">Start a practice</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
