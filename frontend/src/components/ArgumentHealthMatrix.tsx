"use client";

/**
 * ArgumentHealthMatrix — Debate-native argument diagnostic grid.
 *
 * Rows  = contentions / arguments
 * Cols  = Claim · Warrant · Evidence · Impact · Weighing
 * Cells = strong ● / weak ⚠ / missing ✗ / n/a —
 *
 * This is not a generic table. It is a tactical flow diagnostic board.
 */

import { motion } from "motion/react";
import { EASE } from "@/lib/motion";

export type CellStatus = "strong" | "weak" | "missing" | "na";

export interface MatrixRow {
  label: string;
  type: "offense" | "defense" | "weighing" | "response";
  /** [claim, warrant, evidence, impact, weighing] */
  cells: [CellStatus, CellStatus, CellStatus, CellStatus, CellStatus];
}

// ── Visual config ──────────────────────────────────────────────────────────────

const COLS = ["Claim", "Warrant", "Evidence", "Impact", "Weighing"] as const;

const CELL: Record<CellStatus, { bg: string; text: string; symbol: string; title: string }> = {
  strong:  { bg: "bg-ok/10 border-ok/30",       text: "text-ok",      symbol: "●", title: "Strong"  },
  weak:    { bg: "bg-warn/10 border-warn/30",    text: "text-warn",    symbol: "⚠", title: "Weak"    },
  missing: { bg: "bg-danger/8 border-danger/20", text: "text-danger",  symbol: "✗", title: "Missing" },
  na:      { bg: "bg-surface-2 border-hairline", text: "text-ink-faint",symbol: "—", title: "N/A"   },
};

const TYPE_BADGE: Record<MatrixRow["type"], { label: string; color: string }> = {
  offense:  { label: "OFF",  color: "bg-ok/15 text-ok"       },
  defense:  { label: "DEF",  color: "bg-blue/15 text-blue"   },
  weighing: { label: "WGH",  color: "bg-violet/15 text-violet"},
  response: { label: "RSP",  color: "bg-orange/15 text-orange"},
};

// ── Demo data (landing page only) ────────────────────────────────────────────

export const DEMO_ROWS: MatrixRow[] = [
  { label: "C1: Economic Harm",    type: "offense",  cells: ["strong", "strong", "weak",    "strong", "missing"] },
  { label: "C2: Poverty Harms",    type: "offense",  cells: ["strong", "weak",   "strong",  "strong", "missing"] },
  { label: "NC1: Growth Tradeoff", type: "defense",  cells: ["strong", "strong", "strong",  "weak",   "weak"   ] },
  { label: "Weighing Block",       type: "weighing", cells: ["na",     "na",     "na",      "strong", "strong" ] },
];

// ── Component ─────────────────────────────────────────────────────────────────

interface ArgumentHealthMatrixProps {
  rows?: MatrixRow[];
  /** Hides the legend row */
  compact?: boolean;
  className?: string;
}

export default function ArgumentHealthMatrix({
  rows = DEMO_ROWS,
  compact = false,
  className = "",
}: ArgumentHealthMatrixProps) {
  const colCount = COLS.length;
  const gridCols = `minmax(0,1.4fr) repeat(${colCount}, minmax(0, 1fr))`;

  return (
    <div className={`flex flex-col gap-2 ${className}`}>

      {/* Column headers */}
      <div className="grid items-end gap-1.5" style={{ gridTemplateColumns: gridCols }}>
        <div /> {/* empty row-label cell */}
        {COLS.map((col) => (
          <div key={col} className="flex justify-center">
            <span className="text-[9px] font-bold uppercase tracking-wider text-ink-faint">
              {col}
            </span>
          </div>
        ))}
      </div>

      {/* Data rows */}
      {rows.map((row, ri) => {
        const badge = TYPE_BADGE[row.type];
        return (
          <motion.div
            key={ri}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: ri * 0.06, ease: EASE }}
            className="grid items-center gap-1.5"
            style={{ gridTemplateColumns: gridCols }}
          >
            {/* Row label + type badge */}
            <div className="flex min-w-0 items-center gap-1.5 pr-1">
              <span className={`shrink-0 rounded px-1 py-0.5 text-[8px] font-bold ${badge.color}`}>
                {badge.label}
              </span>
              <p className="truncate text-[10px] font-medium text-ink-subtle">{row.label}</p>
            </div>

            {/* Status cells */}
            {row.cells.map((status, ci) => {
              const s = CELL[status];
              return (
                <div
                  key={ci}
                  className={`flex h-8 items-center justify-center rounded border text-[11px] font-bold ${s.bg} ${s.text}`}
                  title={`${row.label} · ${COLS[ci]}: ${s.title}`}
                  aria-label={`${COLS[ci]}: ${s.title}`}
                >
                  {s.symbol}
                </div>
              );
            })}
          </motion.div>
        );
      })}

      {/* Legend */}
      {!compact && (
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-hairline pt-2">
          {(["strong", "weak", "missing"] as CellStatus[]).map((s) => (
            <div key={s} className="flex items-center gap-1">
              <span className={`text-[10px] font-bold ${CELL[s].text}`}>{CELL[s].symbol}</span>
              <span className="text-[9px] capitalize text-ink-faint">{CELL[s].title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
