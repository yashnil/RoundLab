"use client";
import { Clock, BookOpen, Mic, RefreshCw, MessageSquare, Users } from "lucide-react";
import type { PracticeAgendaItem } from "@/types/training";

const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  review: <BookOpen size={13} className="text-lav" aria-hidden />,
  drill: <Users size={13} className="text-ok" aria-hidden />,
  partner_exercise: <Users size={13} className="text-blue-400" aria-hidden />,
  rerecord: <RefreshCw size={13} className="text-warn" aria-hidden />,
  reflection: <MessageSquare size={13} className="text-ink-subtle" aria-hidden />,
};

const ACTIVITY_LABEL: Record<string, string> = {
  review: "Review",
  drill: "Drill",
  partner_exercise: "Partner Exercise",
  rerecord: "Re-record",
  reflection: "Reflection",
};

interface Props {
  items: PracticeAgendaItem[];
  totalMinutes: number;
}

export function PracticeAgenda({ items, totalMinutes }: Props) {
  const usedMinutes = items.reduce((s, i) => s + i.duration_minutes, 0);

  return (
    <div className="space-y-3" role="region" aria-label="Practice agenda">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">Practice Agenda</p>
        <div className="flex items-center gap-1 text-[11px] text-ink-subtle">
          <Clock size={11} aria-hidden />
          {usedMinutes} / {totalMinutes} min
        </div>
      </div>

      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-3 rounded-xl border border-hairline bg-surface-1 px-3 py-2.5">
          <div className="w-8 h-8 rounded-lg border border-hairline bg-surface-2 flex items-center justify-center shrink-0">
            {ACTIVITY_ICONS[item.activity_type] ?? <Mic size={13} aria-hidden />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
                {ACTIVITY_LABEL[item.activity_type] ?? item.activity_type}
              </span>
              <span className="text-[10px] text-ink-faint">{item.duration_minutes} min</span>
            </div>
            <p className="text-[12px] font-medium text-ink mt-0.5">{item.description}</p>
            <p className="text-[11px] text-ink-subtle mt-0.5 italic">{item.team_data_reason}</p>
          </div>
        </div>
      ))}

      {items.length === 0 && (
        <div className="rounded-xl border border-hairline bg-surface-1 px-4 py-6 text-center">
          <p className="text-[13px] text-ink-subtle">No agenda generated yet.</p>
        </div>
      )}
    </div>
  );
}
