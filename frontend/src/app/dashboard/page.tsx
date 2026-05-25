import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-8 px-6 py-16">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Dashboard
        </h1>
        <Button asChild>
          <Link href="/session">New Session</Link>
        </Button>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <p className="text-zinc-400">No sessions yet.</p>
          <p className="text-sm text-zinc-400">
            Record or upload a speech to get your first flow.
          </p>
          <Button asChild variant="outline" className="mt-2">
            <Link href="/session">Start a Session</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
