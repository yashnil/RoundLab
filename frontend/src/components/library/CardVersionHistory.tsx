"use client";

import { useState, useEffect } from "react";
import { Clock, RotateCcw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CardVersion } from "@/types/library";

interface CardVersionHistoryProps {
  cardId: string;
  userId: string;
  onRestored?: () => void;
}

export function CardVersionHistory({
  cardId,
  userId,
  onRestored,
}: CardVersionHistoryProps) {
  const [versions, setVersions] = useState<CardVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<number | null>(null);

  useEffect(() => {
    apiFetch(`/library/cards/${cardId}/versions?user_id=${userId}`)
      .then((data) => setVersions((data as CardVersion[]).slice().reverse()))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [cardId, userId]);

  async function restore(versionNumber: number) {
    if (!confirm(`Restore card to version ${versionNumber}? Citation edits will be undone.`)) return;
    setRestoring(versionNumber);
    try {
      await apiFetch(`/library/cards/${cardId}/versions/${versionNumber}/restore`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId, reason: "manual_restore" }),
      });
      onRestored?.();
    } catch {
      // non-fatal
    } finally {
      setRestoring(null);
    }
  }

  if (loading) {
    return <div className="text-[11px] text-ink-subtle">Loading history…</div>;
  }

  if (versions.length === 0) {
    return <p className="text-[11px] text-ink-subtle italic">No version history.</p>;
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 mb-2">
        <Clock size={13} className="text-ink-subtle" />
        <span className="text-[12px] font-semibold text-ink">Version History</span>
      </div>
      {versions.map((v) => {
        const changedFields = Object.keys(v.changed_fields);
        return (
          <div
            key={v.id}
            className="flex items-start gap-3 py-2 px-2.5 rounded-lg border border-hairline hover:bg-surface-muted transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-medium text-ink">
                Version {v.version_number}
                {v.reason && (
                  <span className="ml-1.5 text-ink-subtle font-normal">— {v.reason}</span>
                )}
              </p>
              {changedFields.length > 0 && (
                <p className="text-[10px] text-ink-subtle">
                  Changed: {changedFields.join(", ")}
                </p>
              )}
              <p className="text-[10px] text-ink-faint">
                {new Date(v.created_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={() => restore(v.version_number)}
              disabled={restoring === v.version_number}
              className="flex items-center gap-1 text-[10px] px-2 py-1 rounded border border-border text-ink-subtle hover:text-ink hover:bg-surface-hover transition-colors disabled:opacity-40"
              aria-label={`Restore to version ${v.version_number}`}
            >
              <RotateCcw size={10} />
              Restore
            </button>
          </div>
        );
      })}
    </div>
  );
}
