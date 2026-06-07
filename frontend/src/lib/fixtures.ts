/**
 * Sample speech report fixtures for development and testing.
 *
 * IMPORTANT: These fixtures are for dev/testing only.
 * They are never used in real user flows.
 * Search for FIXTURE_ENABLED to find any feature flags that gate their use.
 */

import type { Speech, Transcript, ArgumentMap, FeedbackReport, Drill } from "@/types";

// ── V1 fixture: report without structured_issues ───────────────────────────────

export const SAMPLE_SPEECH_V1: Speech = {
  id: "fixture-speech-v1",
  user_id: "fixture-user-1",
  title: "1AC — State Practice (Fixture V1)",
  speech_type: "constructive",
  side: "pro",
  judge_type: "flow",
  topic: "Resolved: The USFG should substantially reduce trade barriers.",
  audio_url: null,
  duration_seconds: 112,
  status: "done",
  created_at: "2026-06-01T10:00:00Z",
  updated_at: "2026-06-01T10:02:00Z",
};

export const SAMPLE_TRANSCRIPT_V1: Transcript = {
  id: "fixture-tx-v1",
  speech_id: "fixture-speech-v1",
  text: "Good morning. We affirm. Our first contention is economic growth. Trade barriers impose significant costs on the global economy. According to the IMF, tariffs reduce GDP by 1.2% globally. This matters because economic growth funds healthcare, education, and infrastructure that improve lives. Our second contention is poverty. Trade restrictions harm developing nations most. The World Bank estimates that reducing trade barriers would lift 300 million people out of poverty. This is a direct, measurable humanitarian benefit.",
  word_count: 84,
  created_at: "2026-06-01T10:01:00Z",
};

export const SAMPLE_ARGUMENT_MAP_V1: ArgumentMap = {
  id: "fixture-argmap-v1",
  speech_id: "fixture-speech-v1",
  arguments: [
    {
      id: "arg_1",
      label: "C1: Economic Growth",
      claim: "Trade barriers impose significant costs on the global economy.",
      warrant: "Higher tariffs raise input costs, reducing trade volumes and economic efficiency.",
      evidence: "IMF study: tariffs reduce GDP by 1.2% globally.",
      impact: "Reduced GDP means less funding for healthcare, education, and infrastructure.",
      argument_type: "offense",
      issues: [],
      confidence: 0.82,
    },
    {
      id: "arg_2",
      label: "C2: Poverty Reduction",
      claim: "Trade restrictions harm developing nations most.",
      warrant: "Developing nations depend on export access; barriers cut their market access disproportionately.",
      evidence: "World Bank: reducing barriers lifts 300M from poverty.",
      impact: "300 million people lifted out of poverty — direct humanitarian benefit.",
      argument_type: "offense",
      issues: ["no weighing"],
      confidence: 0.75,
    },
  ],
  created_at: "2026-06-01T10:01:30Z",
};

export const SAMPLE_FEEDBACK_V1: FeedbackReport = {
  id: "fixture-fb-v1",
  speech_id: "fixture-speech-v1",
  overall_score: 62,
  scores: { clash: 10, weighing: 9, extensions: 14, drops: 16, judge_adaptation: 13 },
  summary: "Strong warranting on C1, but impact weighing is absent. The C2 poverty argument needs explicit magnitude comparison against opponent offense. A flow judge will need the warranting to be crisper.",
  strengths: [
    "C1 warrant chain is explicit: claim → IMF evidence → GDP impact",
    "C2 has a compelling humanitarian impact that is clearly stated",
  ],
  weaknesses: [
    "No explicit weighing on either contention — flow judge may not vote on magnitude alone",
    "C2 lacks a warrant explaining WHY developing nations are disproportionately harmed",
  ],
  raw_feedback: {
    decision_logic: "Pro is likely winning on C1 economic growth given the strong IMF warrant, but C2 needs a clearer warrant to be evaluated. Con has no competing offense yet, so the round turns on whether C1 is persuasively weighed.",
    top_3_priorities: [
      "Add explicit impact weighing comparing magnitude, probability, and timeframe",
      "Strengthen C2 warrant to explain the mechanism of harm on developing nations",
      "Extend offense beyond stating impacts — explain why Pro outweighs",
    ],
    warranting_diagnostics: [
      "C1: warrant present — IMF citation links claim to evidence clearly",
      "C2: warrant is thin — 'harm developing nations most' is asserted but not mechanistically explained",
    ],
    weighing_diagnostics: [
      "C1: impact stated (GDP) but not weighed against opponent offense",
      "C2: poverty impact stated but no magnitude, probability, or timeframe comparison",
    ],
    dropped_or_undercovered_arguments: [],
    evidence_diagnostics: [
      "IMF citation: present but no date or specificity on tariff type",
      "World Bank citation: present but no clarification of reduction scenario",
    ],
    recommendations: [
      "Practice a 90-second weighing sprint comparing magnitude, probability, timeframe",
      "Drill C2 warrant: 'Developing nations are harmed most because [mechanism]'",
    ],
    // V1 report: no structured_issues field
  },
  created_at: "2026-06-01T10:02:00Z",
};

// ── V2 fixture: report with structured_issues ──────────────────────────────────

export const SAMPLE_SPEECH_V2: Speech = {
  ...SAMPLE_SPEECH_V1,
  id: "fixture-speech-v2",
  title: "1AC — State Practice (Fixture V2)",
};

export const SAMPLE_FEEDBACK_V2: FeedbackReport = {
  ...SAMPLE_FEEDBACK_V1,
  id: "fixture-fb-v2",
  speech_id: "fixture-speech-v2",
  raw_feedback: {
    ...SAMPLE_FEEDBACK_V1.raw_feedback,
    structured_issues: [
      {
        issue_type: "no_weighing",
        severity: "high",
        title: "No impact weighing on either contention",
        explanation: "Both C1 and C2 state impacts but never compare them to opponent offense on magnitude, probability, or timeframe.",
        why_it_matters: "A flow judge will not vote on stated impacts alone — they need explicit comparison to evaluate which side wins.",
        recommendation: "Add a weighing block after each impact: 'This outweighs [opponent impact] because [magnitude/probability/timeframe].'",
        affected_argument_labels: ["C1: Economic Growth", "C2: Poverty Reduction"],
        recommended_drill_type: "weighing",
      },
      {
        issue_type: "missing_warrant",
        severity: "medium",
        title: "C2 warrant is asserted, not explained",
        explanation: "C2 claims developing nations are harmed most but doesn't explain the mechanism linking trade restrictions to that disproportionate harm.",
        why_it_matters: "Without a warrant, the claim is vulnerable to a flat denial — opponent can simply say 'that's not true' and win the argument.",
        recommendation: "Add: 'Developing nations rely on export-led growth — barriers cut off their primary income source, unlike developed nations with diversified economies.'",
        affected_argument_labels: ["C2: Poverty Reduction"],
        recommended_drill_type: "warranting",
      },
    ],
  },
};

export const SAMPLE_DRILLS_V2: Drill[] = [
  {
    id: "fixture-drill-1",
    speech_id: "fixture-speech-v2",
    user_id: "fixture-user-1",
    title: "Impact Weighing Comparison Sprint",
    description: "Practice comparing impacts explicitly using magnitude, probability, and timeframe.",
    skill_target: "weighing",
    prompt: "Take your C1 economic growth impact and compare it against a hypothetical opponent impact (e.g. 'tariffs protect domestic jobs'). In 60 seconds, explain why your impact outweighs using at least two of: magnitude, probability, timeframe, reversibility.",
    order: 1,
    instructions: "1. State your impact clearly.\n2. Name the opponent impact.\n3. Compare on magnitude: who is affected more?\n4. Compare on probability: which harm is more likely?\n5. Compare on timeframe: which is more immediate?",
    success_criteria: [
      "Uses at least two weighing criteria (magnitude, probability, timeframe)",
      "Directly names the opponent impact before comparing",
      "Concludes with a clear statement of why you outweigh",
    ],
    source_weakness: "No explicit weighing on either contention",
    difficulty: "intermediate",
    status: "assigned",
    time_limit_seconds: 90,
    created_at: "2026-06-01T10:03:00Z",
  },
  {
    id: "fixture-drill-2",
    speech_id: "fixture-speech-v2",
    user_id: "fixture-user-1",
    title: "C2 Warrant Chain Drill",
    description: "Strengthen the mechanical link on the poverty contention.",
    skill_target: "warranting",
    prompt: "Re-deliver C2 (poverty) with a clear warrant explaining WHY developing nations are disproportionately harmed by trade barriers. You have 45 seconds to state: claim, warrant (mechanism), evidence, impact.",
    order: 2,
    instructions: "1. State the claim: 'Trade restrictions harm developing nations most.'\n2. Give the warrant — explain the MECHANISM: 'Because developing nations rely on export-led growth...'\n3. Cite the evidence: World Bank / IMF stat.\n4. State the impact: poverty numbers, magnitude.",
    success_criteria: [
      "Warrant explains a mechanism (not just repeats the claim)",
      "Evidence is cited with source name",
      "Impact is quantified with a number",
    ],
    source_weakness: "C2 warrant is asserted, not explained",
    difficulty: "beginner",
    status: "assigned",
    time_limit_seconds: 60,
    created_at: "2026-06-01T10:03:01Z",
  },
  {
    id: "fixture-drill-3",
    speech_id: "fixture-speech-v2",
    user_id: "fixture-user-1",
    title: "Lay Judge Summary Drill",
    description: "Translate your arguments into plain language for a non-expert judge.",
    skill_target: "judge_adaptation",
    prompt: "Re-deliver your constructive case for a lay judge in 90 seconds. Replace debate jargon with plain English. Focus on: what is the harm, who is affected, why the government's action causes or prevents it.",
    order: 3,
    instructions: "1. Avoid 'warrant', 'impact', 'weighing' — use plain English.\n2. Tell a story: 'Here's the problem, here's the proof, here's why it matters.'\n3. Use real-world analogies.\n4. End with one clear reason to vote Pro.",
    success_criteria: [
      "No debate jargon (no 'extend', 'impact calculus', 'contention')",
      "Ends with one clear voting reason in plain English",
      "Uses a real-world example or analogy",
    ],
    source_weakness: "Adaptation for lay judge",
    difficulty: "intermediate",
    status: "assigned",
    time_limit_seconds: 120,
    created_at: "2026-06-01T10:03:02Z",
  },
];
