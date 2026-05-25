import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-10 bg-zinc-50 px-6 py-24 dark:bg-zinc-950">
      <div className="flex flex-col items-center gap-4 text-center">
        <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-700 dark:bg-blue-900 dark:text-blue-300">
          Beta
        </span>
        <h1 className="text-5xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          RoundLab
        </h1>
        <p className="max-w-md text-lg text-zinc-500 dark:text-zinc-400">
          AI flow coach for novice and JV Public Forum debaters. Record a
          speech, get instant structured feedback.
        </p>
        <div className="mt-2 flex gap-3">
          <Button asChild size="lg">
            <Link href="/dashboard">Get Started</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/session">Try a Session</Link>
          </Button>
        </div>
      </div>

      <div className="grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            title: "Flow Table",
            body: "Auto-extract claims, warrants, evidence, and impacts into a structured flow.",
          },
          {
            title: "Ballot Feedback",
            body: "Get ballot-style feedback on weighing, extensions, drops, and judge adaptation.",
          },
          {
            title: "Drills",
            body: "Receive three personalized practice drills tied directly to your weaknesses.",
          },
        ].map((f) => (
          <Card key={f.title}>
            <CardContent className="pt-6">
              <p className="mb-1 font-semibold text-zinc-800 dark:text-zinc-100">
                {f.title}
              </p>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {f.body}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
