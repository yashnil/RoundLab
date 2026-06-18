# Anti–Vibe-Coded Checklist

A standing checklist applied before calling any surface "done." Status reflects the
**public homepage** after the Phase 2 pass; other surfaces are tracked for their phases.

> **What makes this interface unmistakably RoundLab?**
> Left-to-right **argument/provenance flow lines** (Claim → Warrant → Evidence → Impact;
> Search → Source → Quote → Card), **parallel debate lanes** (Original vs Re-record,
> source vs AI), a consistent **judge-lens** that reorders meaning rather than swapping a
> badge, and **restrained training pulse** progress — never XP confetti. Editorial reading
> type for ballots/quotes; dense tabular type for scores/timers.

## Generated-app smells — homepage status

| Smell | Status | Notes |
| --- | --- | --- |
| Every concept in a rounded bordered card | ✅ fixed | Acts use varied density/scale; flow + lanes use crisp connectors, not nested cards |
| Identical section layouts | ✅ fixed | Each act has a distinct layout (strip, full-width board, lanes, trail, grid) |
| Excessive purple/blue AI gradients | ✅ controlled | Single restrained `lav` accent; ambient glow limited to hero |
| Arbitrary glows / sparkles / robot icons | ✅ | Icons are debate-functional (Mic, scale, gavel-as-text); no sparkles |
| Repeated "AI-powered" copy | ✅ | Copy is action/debate-native; AI labeled only where authorship matters |
| Empty dashboards / zeroed metrics | n/a (homepage) | Proof strip uses real product facts, not zeros |
| Unexplained scores | ✅ | Scores shown with the behavior that caused them (added warrant/weighing) |
| Feature grids with interchangeable icons | ✅ fixed | Removed the bento; "Supported today" links to real surfaces |
| Huge titles over sparse content | ✅ | Each act carries a concrete artifact |
| Too many badges / tiny gray text | ⚠ ongoing | Minimum text sizes kept ≥ 10px on labels; watch contrast |
| Nested cards inside cards | ✅ fixed | Flattened section visuals |
| Generic sidebar + header + stat cards | n/a (homepage) | — |
| Fake progress % / fake waveform | ✅ fixed | Removed decorative hardcoded waveform from how-it-works; hero waveform is one-shot + `aria-hidden` and clearly illustrative |
| Generic spinner / random Framer entrances | ✅ | Motion via shared presets, all under global reduced-motion kill-switch |
| Tooltips compensating for unclear UI | ✅ | Labels are self-explanatory |
| Overuse of glass effects | ✅ controlled | Backdrop-blur limited to sticky nav + hero panel |
| UI designed around DB tables not tasks | ✅ | Sections map to user jobs (practice, improve, research, coach) |
| Different design language per route | ✅ (homepage internally coherent) | Cross-route consistency tracked in later phases |
| Features that exist but appear disconnected | ✅ fixed | Roadmap → "Supported today" links to live routes |
| Buttons labeled Submit/Process/Generate | ✅ | "Start practicing", "See a real report", "Open Evidence Studio" |
| Scores without causal explanation | ✅ | Improvement lane ties change to behavior |
| AI text mixed with source text | ✅ | Evidence trail visually separates exact quote (source) from tag (AI) |
| XP-heavy game visuals | ✅ fixed | Removed "+50 XP" chip from hero console |

## Enforced by tests

- `frontend/src/__tests__/marketing.test.ts`
  - Fails if any marketing/footer/supported-today copy contains roadmap/"coming soon"
    language.
  - Fails if any nav/footer target is not an in-app route or an on-page anchor.
  - Asserts the "Supported today" list is non-empty and every entry links somewhere real.

## Remaining (non-blocking)

- Re-run with a browser tool to capture `artifacts/ui-after/` and verify contrast at 200% zoom.
- Carry the visual language to `/login`, dashboard, report, evidence, team in their phases.
