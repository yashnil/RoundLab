# Dissio UI Research Notes

Research informing the product-wide visual transformation. Sources examined,
patterns adopted/rejected, and how they map to Dissio specifically.

## Sources examined

- **Vercel Web Interface Guidelines** (vercel-labs/web-interface-guidelines) —
  ~100 rules / 17 categories, WCAG-based.
- **AI processing / job-progress UX** — Smashing Magazine "Practical Interface
  Patterns for AI Transparency," Telerik "Loading UI/UX Patterns for AI Apps,"
  codewithcaptain "AI Progress Indicators," Salesforce "Trustworthy AI UX."
- Internal: existing Dissio shell, tokens, and `useSpeechProcessing` lifecycle.

## Patterns adopted

- **Audit all 7 states per component** (Vercel): hover, focus-visible, active,
  disabled, loading, empty, error. Missing states are findings. → Dissio
  interaction tokens (§5) standardize these.
- **Visible focus ring always** (never `outline:none` without replacement),
  **44×44px** touch targets, semantic `<a href>` / `<button>`, labels associated
  with every control. → Already in the shell; reinforced product-wide.
- **Dynamic checklists / timeline chips beat progress bars** for unpredictable
  AI timing — users stay patient when they can see *where* the system is. → Keep
  Dissio's honest stage list; never a fake percentage.
- **Name what's being analyzed** ("Evaluating transaction patterns"). → Dissio
  processing names the real categories: argument structure, evidence, clash,
  weighing, judge adaptation, delivery, drills.
- **Honesty over concealment** — transparency signals trust. → "saved unless
  proven" capture status; honest leave-page copy.

## Patterns rejected

- Fake/animated progress bars and fabricated percentages.
- Background/continuous gradient motion and decorative shimmer.
- Generic violet-AI gradient identity (we use a restrained lavender accent +
  debate-semantic colors instead).
- Radar charts where unreadable; giant equal-weight stat-card grids.

## Dissio-specific design direction

Dissio's identity comes from **debate structure**, not generic SaaS chrome:

- **Flow semantics** — live / contested / dropped arguments get consistent,
  meaning-bearing colors everywhere (flow, report, drills, progress).
- **Evidence integrity** — strong / weak / unverified, plus a hard visual line
  between *exact source quote*, *AI-generated explanation*, and *user edits*.
- **Authorship provenance** — coach-authored vs AI-generated vs user-authored
  content is always visually distinguishable (coach review, reports).
- **Pro/Con framing** and **judge-lens markers** as structural, not decorative.
- **Skill trajectory** — improving / declining / insufficient-data as a shared
  vocabulary across reports, drills, and progress.

These map to a shared semantic-token layer (this pass) so every surface speaks
the same visual language instead of re-inventing colors per feature.

## Sources

- [Vercel Web Interface Guidelines (GitHub)](https://github.com/vercel-labs/web-interface-guidelines)
- [Vercel Web Interface Guidelines summary](https://www.holgerscode.com/blog/2025/09/21/vercel-web-interface-guidelines/)
- [Practical Interface Patterns for AI Transparency — Smashing Magazine](https://www.smashingmagazine.com/2026/05/practical-interface-patterns-ai-transparency/)
- [Loading UI/UX Patterns for AI Applications — Telerik](https://www.telerik.com/blogs/loading-ui-ux-patterns-ai-applications)
- [Design AI Progress Indicators — codewithcaptain](https://codewithcaptain.com/design-ai-progress-indicators/)
- [6 UX Design Tips to Make AI Trustworthy — Salesforce](https://www.salesforce.com/blog/6-ux-design-tips-trust-ai/)
