import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function SessionPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-8 px-6 py-16">
      <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        New Session
      </h1>

      <Card>
        <CardContent className="flex flex-col items-center gap-6 py-12 text-center">
          {/* Microphone button placeholder */}
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
            <span className="text-3xl">🎙️</span>
          </div>
          <div className="flex flex-col gap-1">
            <p className="font-semibold text-zinc-800 dark:text-zinc-100">
              Record a Speech
            </p>
            <p className="text-sm text-zinc-500">
              Tap to start recording. Stop when your speech is complete.
            </p>
          </div>
          <Button disabled className="w-40">
            Record (coming soon)
          </Button>
        </CardContent>
      </Card>

      <div className="flex items-center gap-4">
        <hr className="flex-1 border-zinc-200 dark:border-zinc-800" />
        <span className="text-sm text-zinc-400">or upload a file</span>
        <hr className="flex-1 border-zinc-200 dark:border-zinc-800" />
      </div>

      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
          <p className="text-sm text-zinc-500">
            Drop an audio file here, or click to browse.
          </p>
          <Button disabled variant="outline">
            Upload (coming soon)
          </Button>
        </CardContent>
      </Card>

      <div className="rounded-lg border border-dashed border-zinc-300 p-6 text-center dark:border-zinc-700">
        <p className="text-sm text-zinc-400">
          Your flow table and feedback will appear here after processing.
        </p>
      </div>
    </main>
  );
}
