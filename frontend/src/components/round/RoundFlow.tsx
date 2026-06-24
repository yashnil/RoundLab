"use client";

import {
  ARGUMENT_STATUS_COLORS,
  ARGUMENT_STATUS_LABELS,
  getConArguments,
  getProArguments,
} from "@/lib/roundModel";
import type { RoundArgument } from "@/types/round";

interface Props {
  arguments: RoundArgument[];
}

function ArgumentRow({ arg }: { arg: RoundArgument }) {
  const statusColor = ARGUMENT_STATUS_COLORS[arg.status] ?? "text-muted-foreground";
  const statusLabel = ARGUMENT_STATUS_LABELS[arg.status] ?? arg.status;
  return (
    <div className="py-2 px-3 border-b last:border-0 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs text-muted-foreground w-8 shrink-0">{arg.label}</span>
        <span className="flex-1 truncate text-xs">{arg.claim}</span>
        <span className={`text-xs shrink-0 ${statusColor}`}>{statusLabel}</span>
      </div>
      {arg.evidence_card_id && (
        <div className="mt-0.5 ml-8 text-xs text-muted-foreground">
          evidence attached
        </div>
      )}
    </div>
  );
}

function SideColumn({ label, args }: { label: string; args: RoundArgument[] }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="sticky top-0 bg-background/90 py-1 px-3 border-b">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span className="ml-2 text-xs text-muted-foreground">({args.length})</span>
      </div>
      {args.length === 0 ? (
        <p className="text-xs text-muted-foreground py-4 px-3 italic">No arguments yet.</p>
      ) : (
        args.map((a) => <ArgumentRow key={a.id} arg={a} />)
      )}
    </div>
  );
}

export function RoundFlow({ arguments: args }: Props) {
  const proArgs = getProArguments(args);
  const conArgs = getConArguments(args);

  return (
    <div className="h-full flex flex-col border rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b bg-muted/30">
        <span className="text-xs font-semibold">Live Round Flow</span>
      </div>
      <div className="flex flex-1 overflow-auto divide-x">
        <SideColumn label="Pro" args={proArgs} />
        <SideColumn label="Con" args={conArgs} />
      </div>
    </div>
  );
}
