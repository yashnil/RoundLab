/**
 * Static eval results fixture for the /evals development dashboard.
 *
 * IMPORTANT: This is DEVELOPMENT DATA ONLY.
 * These are representative results from running:
 *   python -m evals.run_evals --mock
 *
 * In mock mode the pipeline uses the expected values as simulated LLM output,
 * so metrics reflect the eval machinery, not real model accuracy.
 * Run the real pipeline (without --mock) for production accuracy numbers.
 *
 * To update this file: copy the output of evals/results/latest.json here.
 */

export interface IssuemetricsDef {
  precision: number;
  recall: number;
  f1: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
}

export interface EvalSampleResult {
  fixture_id: string;
  fixture_title: string;
  speech_type: string;
  mock_mode: boolean;
  issue_metrics: IssuemetricsDef;
  argument_coverage: number;
  drill_relevance: number;
  hallucinated_evidence_count: number;
  required_issues_missed: string[];
  passed: boolean;
  error: string | null;
  timestamp: string;
}

export interface EvalRunResult {
  run_id: string;
  timestamp: string;
  mock_mode: boolean;
  total_fixtures: number;
  passed: number;
  failed: number;
  avg_issue_precision: number;
  avg_issue_recall: number;
  avg_issue_f1: number;
  avg_argument_coverage: number;
  avg_drill_relevance: number;
  total_hallucinated_evidence: number;
  samples: EvalSampleResult[];
}

/** Sample mock-mode eval results — used as a static fixture on the /evals page. */
export const SAMPLE_EVAL_RESULTS: EvalRunResult = {
  run_id: "mock_sample_2026_06_08",
  timestamp: "2026-06-08T03:44:27Z",
  mock_mode: true,
  total_fixtures: 8,
  passed: 8,
  failed: 0,
  avg_issue_precision: 1.0,
  avg_issue_recall: 1.0,
  avg_issue_f1: 1.0,
  avg_argument_coverage: 1.0,
  avg_drill_relevance: 1.0,
  total_hallucinated_evidence: 0,
  samples: [
    {
      fixture_id: "good_constructive",
      fixture_title: "Strong 1AC — Economic Burden & Escalation Case",
      speech_type: "constructive",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 1, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:27Z",
    },
    {
      fixture_id: "missing_warrant_constructive",
      fixture_title: "Weak 1AC — Claims Without Mechanisms",
      speech_type: "constructive",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 3, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:28Z",
    },
    {
      fixture_id: "weak_evidence_constructive",
      fixture_title: "1AC With Vague Evidence Citations",
      speech_type: "constructive",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 1, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:29Z",
    },
    {
      fixture_id: "no_weighing_summary",
      fixture_title: "Summary That Extends Without Weighing",
      speech_type: "summary",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 1, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:30Z",
    },
    {
      fixture_id: "dropped_argument_rebuttal",
      fixture_title: "Rebuttal That Drops Opponent Contention 2",
      speech_type: "rebuttal",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 1, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:31Z",
    },
    {
      fixture_id: "new_argument_final_focus",
      fixture_title: "Final Focus With New Evidence",
      speech_type: "final_focus",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 1, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:32Z",
    },
    {
      fixture_id: "no_clash_rebuttal",
      fixture_title: "Rebuttal That Only Restates Own Case",
      speech_type: "rebuttal",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 2, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:33Z",
    },
    {
      fixture_id: "strong_delivery_weak_logic",
      fixture_title: "Confident Delivery With Circular Arguments",
      speech_type: "constructive",
      mock_mode: true,
      issue_metrics: { precision: 1.0, recall: 1.0, f1: 1.0, true_positives: 3, false_positives: 0, false_negatives: 0 },
      argument_coverage: 1.0,
      drill_relevance: 1.0,
      hallucinated_evidence_count: 0,
      required_issues_missed: [],
      passed: true,
      error: null,
      timestamp: "2026-06-08T03:44:34Z",
    },
  ],
};
