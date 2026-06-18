import { Shield, FileLock, Users, Lock, AlertCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { TRUST_POINTS } from "@/lib/marketing";

const ICONS: LucideIcon[] = [Shield, FileLock, Users, Lock, AlertCircle];

export default function TrustGrid() {
  return (
    <div className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-hairline bg-hairline sm:grid-cols-2 lg:grid-cols-3">
      {TRUST_POINTS.map((point, i) => {
        const Icon = ICONS[i % ICONS.length];
        return (
          <div key={point.title} className="flex flex-col gap-2.5 bg-surface-1 p-5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-hairline bg-surface-2">
              <Icon size={15} className="text-lav" aria-hidden />
            </div>
            <p className="text-sm font-semibold text-ink">{point.title}</p>
            <p className="text-xs leading-relaxed text-ink-subtle">{point.body}</p>
          </div>
        );
      })}
    </div>
  );
}
