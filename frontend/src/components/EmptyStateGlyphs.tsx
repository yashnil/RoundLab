/**
 * EmptyStateGlyphs — debate-native SVG illustrations for empty states.
 *
 * All components:
 * - Pure SVG, no external assets
 * - Debate-specific (not generic cloud/box icons)
 * - `currentColor` fill/stroke so they inherit text color from parent
 * - Accessible (aria-hidden by default)
 */

interface GlyphProps {
  className?: string;
}

/** Mini ruled flow sheet with empty rows — use when no speeches / no flow */
export function EmptyFlowGlyph({ className = "" }: GlyphProps) {
  return (
    <svg
      viewBox="0 0 60 50"
      fill="none"
      className={className}
      aria-hidden
    >
      {/* Document border */}
      <rect x="2" y="2" width="56" height="46" rx="2" stroke="currentColor" strokeWidth="1.2" />
      {/* Left margin rule */}
      <line x1="13" y1="2" x2="13" y2="48" stroke="currentColor" strokeWidth="0.7" strokeDasharray="2 2" opacity="0.5" />
      {/* Ruled lines — 4 empty rows */}
      <line x1="16" y1="13" x2="52" y2="13" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
      <line x1="16" y1="21" x2="52" y2="21" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
      <line x1="16" y1="29" x2="52" y2="29" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
      <line x1="16" y1="37" x2="52" y2="37" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
      {/* Corner fold */}
      <path d="M 46 2 L 58 14" stroke="currentColor" strokeWidth="0.8" opacity="0.4" />
      <path d="M 46 2 L 46 14 L 58 14" stroke="currentColor" strokeWidth="0.8" fill="none" opacity="0.3" />
    </svg>
  );
}

/** Closed case file folder with tab — use when no evidence documents */
export function EmptyEvidenceGlyph({ className = "" }: GlyphProps) {
  return (
    <svg
      viewBox="0 0 60 48"
      fill="none"
      className={className}
      aria-hidden
    >
      {/* Folder body */}
      <path
        d="M 2 18 L 2 44 Q 2 46 4 46 L 56 46 Q 58 46 58 44 L 58 18 Z"
        stroke="currentColor" strokeWidth="1.2"
      />
      {/* Folder tab */}
      <path
        d="M 2 18 L 2 14 Q 2 12 4 12 L 22 12 Q 24 12 25 14 L 27 18 Z"
        stroke="currentColor" strokeWidth="1.2"
      />
      {/* Document lines inside */}
      <line x1="10" y1="27" x2="50" y2="27" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
      <line x1="10" y1="33" x2="50" y2="33" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
      <line x1="10" y1="39" x2="36" y2="39" stroke="currentColor" strokeWidth="0.8" strokeDasharray="3 2" />
    </svg>
  );
}

/** Rep rail with empty nodes — use when no drill attempts */
export function EmptyDrillGlyph({ className = "" }: GlyphProps) {
  const nodeX = [8, 24, 40, 56, 72];
  return (
    <svg
      viewBox="0 0 80 20"
      fill="none"
      className={className}
      aria-hidden
    >
      {/* Connecting line */}
      <line
        x1="8" y1="10" x2="72" y2="10"
        stroke="currentColor" strokeWidth="0.8" strokeDasharray="3.5 2"
      />
      {/* Empty square nodes */}
      {nodeX.map(cx => (
        <rect
          key={cx}
          x={cx - 5} y={5} width={10} height={10}
          rx={1.5}
          stroke="currentColor" strokeWidth="1.2"
        />
      ))}
    </svg>
  );
}

/** Pilot dial/gauge — use when no pilot data or analytics */
export function EmptyPilotGlyph({ className = "" }: GlyphProps) {
  return (
    <svg
      viewBox="0 0 60 38"
      fill="none"
      className={className}
      aria-hidden
    >
      {/* Gauge arc (half circle) */}
      <path
        d="M 4 34 A 26 26 0 0 1 56 34"
        stroke="currentColor" strokeWidth="1.2" strokeDasharray="3 2"
      />
      {/* Tick marks at -60°, -30°, 0°, +30°, +60° from top */}
      {[-60, -30, 0, 30, 60].map((deg) => {
        const rad = ((deg - 90) * Math.PI) / 180;
        const inner = 20, outer = 24;
        const x1 = 30 + inner * Math.cos(rad);
        const y1 = 34 + inner * Math.sin(rad);
        const x2 = 30 + outer * Math.cos(rad);
        const y2 = 34 + outer * Math.sin(rad);
        return (
          <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke="currentColor" strokeWidth="1" />
        );
      })}
      {/* Needle at far left (zero state) */}
      <line
        x1="30" y1="34" x2="10" y2="26"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
      />
      {/* Center pivot */}
      <circle cx="30" cy="34" r="2.5" fill="currentColor" />
    </svg>
  );
}
