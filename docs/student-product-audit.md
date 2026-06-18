# Student Product Audit (Phase 3)

_New, phase-specific findings for the authenticated student loop. Code-grounded;
no browser tooling is available in this environment, so `artifacts/ui-review/`
screenshots are not captured (see homepage audit for the same constraint)._

Branch `ui/homepage-transformation`, continuing from `b2e3986`.

## Shell

- **Sidebar grouped by backend area, not student task.** Was Core / Growth / Team /
  Utility. → Regrouped into **Train / Research / Team / Resources** (`navItems.ts`),
  honest labels, only real routes. _(done — commit `416b73b`)_
- **Command menu was nav-only.** No way to start a specific speech. → Added debate-native
  Start Constructive / Rebuttal / Summary / Final Focus (deep-linked) + Send feedback,
  ordered practice-first. _(done — `416b73b`)_
- **Remaining:** contextual sidebar content (active analysis, unfinished speech, recent
  reports) and a header context bar are not yet wired; the header still mostly mirrors nav.

## Dashboard

- Already rich: cockpit band, next-action panel, quick-start, coaching focus, recent
  activity, mission panel, delivery focus, today's prep, block readiness, skill breakdown,
  trends. **Risk: card overload** — many similar-weight cards; a future pass should prune.
- **No practice recipes** (only bare speech-type quick start). → Added `PracticeRecipes`
  (full speeches + quick reps) deep-linking into a primed setup. _(done — `bffd8df`)_
- **Next-action resolver mislabeled abandoned captures.** A `pending` speech with no audio
  was reported as "being analyzed" (pending ∈ processing statuses). → Added a
  `finish-capture` case checked before resume. _(done — `bffd8df`)_
- **Remaining:** progress-preview module and new-user state are partially served by existing
  cards; a dedicated, de-cluttered layout is still open.

## Practice setup (`/session`)

- Good debate-native guidance + smart judge default already present.
- **Deep-links only honored `?type=`.** → Now honors `?judge=`, `?side=`, `?goal=` so recipes
  carry through; goal shown as on-screen guidance (not persisted). _(done — `bffd8df`)_
- **XP framing** ("earn 50 XP") removed for consistency with the de-gamified language.
- **Remaining:** the form is still plain `<select>` controls — rich speech-type / Pro-Con
  segmented / judge-lens cards (§6) are not yet built; no saved templates.

## Capture / recorder / upload / paste

- `SpeechCaptureWorkspace` has record / upload / paste tabs, an honest shared save-state
  (`CaptureSaveStatus`) and leave-protection — a strong base.
- **Paste was thin:** bare word count, no speaking-time estimate, no minimum guidance, and
  **no delivery limitation** disclosure. → Added `lib/practice/pasteText.ts`
  (word count, ~speaking time, minimum, delivery-limitation copy) wired into the paste UI.
  _(done — this commit)_
- **Remaining:** full recorder state matrix polish (unsupported-browser, too-short,
  finalizing distinctions), upload empty/selected/error refinement, and focus-mode reduction
  of surrounding shell during active recording (§7–§9) are not yet implemented.

## Processing, Report (6 sections), Drill, Comparison, Progress

- Processing has a transparent debate-native timeline (`SpeechProcessingTimeline`); report has
  six-section URL-addressable nav (`SpeechReportNav`). These are solid foundations from prior
  commits but have **not** yet been redesigned to this phase's depth (flow canvas focus/dim,
  ballot decision vs coach split, transcript-first review, drill improvement receipt,
  before/after comparison lanes, progress development workspace).
- **No dedicated `/progress` route** — progress lives inside the dashboard. A development-
  focused Progress surface (§15) remains to build.

## Status summary

Completed this phase so far: student-task shell + command menu, practice recipes + deep-linked
setup, resolver `finish-capture` case, paste delivery-honesty. The processing/report/drill/
comparison/progress redesigns (§11–§15) and the recorder/upload/setup-control redesigns
(§6–§9) are the remaining, larger body of work and continue from here.
