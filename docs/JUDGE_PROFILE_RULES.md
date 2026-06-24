# Judge Profile Rules (Pass 15)

## Built-in Profile Definitions

### Lay Judge
- No debate training. Decides based on clarity, common sense, and narrative.
- **Jargon tolerance: 1** — Replace all debate terms with plain language.
- **Narrative preference: 5** — Story and real-world examples are essential.
- **Intervention tolerance: 4** — May fill in logical gaps themselves.
- **Extension strictness: 1** — Does not track extensions explicitly.

### Parent Judge
- Has attended debates but has not debated. Understands the format.
- **Jargon tolerance: 2** — Define terms on first use.
- **Real-world explanation: 5** — Must connect to tangible consequences.
- **Weighing expectation: 4** — Expects a reason to prefer one side.

### Flow Judge
- Experienced competitive debater who flows every word.
- **Line-by-line expectation: 5** — Every response must be labeled.
- **Extension strictness: 5** — Uncovered extensions are dropped arguments.
- **Jargon tolerance: 4** — Technical debate terms are preferred.
- **Narrative preference: 2** — Story is secondary; argument structure is primary.

### Technical Judge
- Expert evaluator who tracks concessions, burdens, and offense/defense precisely.
- **Technical rule sensitivity: 5** — Procedural arguments (theory, disclosure) are live.
- **Jargon tolerance: 5** — Full debate vocabulary expected.
- **Intervention tolerance: 1** — Only credits explicit arguments on the flow.

### Coach Judge
- Former debater or coach. Rewards strategic soundness and best-practice habits.
- **Source qualification importance: 4** — Cites author credentials briefly.
- **Weighing expectation: 5** — Comparative weighing is required.
- **Line-by-line expectation: 4** — Expects complete structure but allows compression.

## Custom Profiles

Users may create custom profiles via `POST /judge-adaptation/profiles/custom`.
Custom profiles must specify all 13 preference dimensions on a 1-5 scale.
Custom profiles are private by default (is_public = false).

## Preference Dimension Reference

| Dimension | Low (1) | High (5) |
|-----------|---------|----------|
| jargon_tolerance | No jargon allowed | Full vocabulary expected |
| speed_tolerance | Slow, conversational | Fast, competition speed |
| evidence_detail_preference | Impact summary only | Full card + qualifier |
| line_by_line_expectation | 1-2 key responses | Every response labeled |
| extension_strictness | Brief summary OK | Every extension required |
| weighing_expectation | "Our side wins" OK | Explicit 3-dim comparison |
| narrative_preference | Structure first | Story first |
| real_world_explanation | Abstract OK | Concrete analogy required |
| technical_rule_sensitivity | Ignore theory | Theory is live |
| intervention_tolerance | Fills gaps | Only credits what's said |
| organization_preference | Intuitive flow OK | Strict label-first required |
| source_qualification_importance | Source name enough | Author + org + credentials |
| persuasion_vs_flow_emphasis | Tone wins | Technical accuracy wins |

## Profile Comparison

Two profiles differ meaningfully if any single dimension differs by ≥ 2.
Use `profiles_differ_meaningfully(a, b)` from `judge_profiles.py`.
