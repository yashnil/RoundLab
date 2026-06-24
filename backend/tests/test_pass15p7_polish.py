"""
Pass 15.7 — Research angle controls + Debate Prep polish tests.

Verifies:
1. ClaimDecomposition: compact row layout (buttons, not nested card+button)
2. ClaimDecomposition: stale-response seq counter present
3. ClaimDecomposition: handleRunAllAngles aggregates via decomposeClaim
4. ClaimDecomposition: loading/disabled guards
5. DebatePrepPanel: hierarchical sections present (lead, strategic, opposition, crossfire, pairing)
6. DebatePrepPanel: copy actions on weighing, cf_q, cf_a
7. DebatePrepPanel: numbered opposition sequence (1/2/3)
8. Backend content quality: direct_support why_this_card no longer says "This card directly supports"
9. Backend content quality: crossfire_answer no longer says "don't get drawn into the source's tone"
10. Backend content quality: opponent_response no longer says "source's bias"
11. Backend content quality: best_pairing no longer says "Pair it with an impact card"
12. Backend: source_title incorporated into why_this_card when provided
13. Backend: claim text embedded in opponent_response for direct_support
14. Stale-response guard present in handleGenerateCards
15. handleRunAllAngles deduplicates by id
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
BACKEND_ROOT = ROOT / "backend"
FRONTEND_ROOT = ROOT / "frontend"


def _src(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _backend(filename: str) -> str:
    return _src(BACKEND_ROOT / "app" / "services" / filename)


def _component(rel: str) -> str:
    return _src(FRONTEND_ROOT / "src" / rel)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ClaimDecomposition: compact row layout
# ─────────────────────────────────────────────────────────────────────────────

class TestClaimDecompositionLayout(unittest.TestCase):

    def _src(self) -> str:
        return _component("components/evidence/ClaimDecomposition.tsx")

    def test_branch_icons_mapped(self):
        src = self._src()
        self.assertIn("BRANCH_ICON", src)
        for icon in ("Zap", "BarChart2", "TrendingUp", "Shield", "AlertCircle"):
            with self.subTest(icon=icon):
                self.assertIn(icon, src)

    def test_rows_use_single_button_per_branch(self):
        # The row IS the button — no nested button inside a div card
        src = self._src()
        self.assertIn("w-full flex items-center", src)
        # ArrowRight trailing indicator (not a separate "Search" button)
        self.assertIn("ArrowRight", src)

    def test_no_grid_cols_inside_list(self):
        # Rows should be a divide-y list, not a two-column grid
        src = self._src()
        self.assertNotIn("grid-cols-2", src)
        self.assertIn("divide-y", src)

    def test_description_truncated(self):
        src = self._src()
        self.assertIn("truncate", src)

    def test_label_no_wrap(self):
        # Row text must use truncate, not overflow to wrap
        src = self._src()
        # The label div has min-w-0
        self.assertIn("min-w-0", src)

    def test_active_branch_bg_lav(self):
        src = self._src()
        self.assertIn("bg-lav/5", src)

    def test_run_all_in_header_not_footer(self):
        src = self._src()
        # Run all button should be in the header section (before the list)
        header_end = src.find("Angle rows")
        run_all_pos = src.find("Run all")
        self.assertGreater(header_end, 0)
        self.assertLess(run_all_pos, header_end)

    def test_whitespace_nowrap_on_run_all(self):
        src = self._src()
        self.assertIn("whitespace-nowrap", src)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Stale-response protection in evidence page
# ─────────────────────────────────────────────────────────────────────────────

class TestStaleResponseProtection(unittest.TestCase):

    def _page(self) -> str:
        return _component("app/evidence/page.tsx")

    def test_search_seq_ref_declared(self):
        self.assertIn("searchSeqRef", self._page())

    def test_seq_incremented_on_each_search(self):
        src = self._page()
        self.assertIn("++searchSeqRef.current", src)

    def test_stale_guard_check(self):
        src = self._page()
        self.assertIn("seq !== searchSeqRef.current", src)

    def test_decompose_claim_imported(self):
        src = self._page()
        self.assertIn("decomposeClaim", src)

    def test_handle_run_all_angles_declared(self):
        src = self._page()
        self.assertIn("handleRunAllAngles", src)

    def test_run_all_iterates_branches(self):
        src = self._page()
        self.assertIn("for (const branch of branches)", src)

    def test_run_all_deduplicates_by_id(self):
        src = self._page()
        self.assertIn("seenIds", src)
        self.assertIn(".has(card.id)", src)

    def test_run_all_passed_to_claim_decomposition(self):
        src = self._page()
        self.assertIn("onRunAll={handleRunAllAngles}", src)

    def test_finally_guards_set_loading_false(self):
        src = self._page()
        # setCbLoading(false) should be inside a stale check in finally
        self.assertIn("setCbLoading(false)", src)


# ─────────────────────────────────────────────────────────────────────────────
# 3. DebatePrepPanel: hierarchical sections
# ─────────────────────────────────────────────────────────────────────────────

class TestDebatePrepPanelSections(unittest.TestCase):

    def _src(self) -> str:
        return _component("components/evidence/DebatePrepPanel.tsx")

    def test_lead_section_present(self):
        src = self._src()
        self.assertIn("What this card proves", src)

    def test_strategic_use_section(self):
        src = self._src()
        self.assertIn("Strategic use", src)
        self.assertIn("warrant_analysis", src)
        self.assertIn("impact_analysis", src)
        self.assertIn("weighing_angle", src)

    def test_answer_opposition_section(self):
        src = self._src()
        self.assertIn("Answer opposition", src)
        self.assertIn("potential_weakness", src)
        self.assertIn("opponent_response", src)
        self.assertIn("how_to_answer_weakness", src)

    def test_crossfire_section(self):
        src = self._src()
        self.assertIn("Crossfire", src)
        self.assertIn("crossfire_question", src)
        self.assertIn("crossfire_answer", src)

    def test_best_pairing_footer(self):
        src = self._src()
        self.assertIn("Best pairing", src)
        self.assertIn("best_pairing", src)

    def test_numbered_opposition_sequence(self):
        src = self._src()
        # Numbered steps 1, 2, 3 for the opposition sequence
        self.assertIn(">1<", src)
        self.assertIn(">2<", src)
        self.assertIn(">3<", src)

    def test_chevron_down_between_opposition_steps(self):
        src = self._src()
        self.assertIn("ChevronDown", src)

    def test_best_use_badge_in_lead(self):
        src = self._src()
        self.assertIn("Best in {speechUse}", src)

    def test_copy_on_weighing(self):
        src = self._src()
        self.assertIn('copyKey="weighing"', src)

    def test_copy_on_cf_q(self):
        src = self._src()
        self.assertIn('copyKey="cf_q"', src)

    def test_copy_on_cf_a(self):
        src = self._src()
        self.assertIn('copyKey="cf_a"', src)

    def test_divide_y_layout_not_grid(self):
        src = self._src()
        self.assertIn("divide-y", src)
        # Should not have a flat two-column grid wrapping everything
        self.assertNotIn("grid-cols-1 sm:grid-cols-2 gap-2.5", src)

    def test_no_rainbow_colors(self):
        src = self._src()
        for bad in ("amber-", "emerald-", "violet-", "indigo-", "rose-", "bg-blue-"):
            with self.subTest(bad=bad):
                self.assertNotIn(bad, src)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Backend content quality: banned generic phrases gone
# ─────────────────────────────────────────────────────────────────────────────

class TestContentQuality(unittest.TestCase):

    def _cc(self) -> str:
        return _backend("card_cutting.py")

    def test_no_this_card_directly_supports(self):
        src = self._cc()
        self.assertNotIn("This card directly supports", src)

    def test_no_dont_get_drawn_into_tone(self):
        src = self._cc()
        self.assertNotIn("don't get drawn into the source's tone", src)
        self.assertNotIn("don’t get drawn into", src)

    def test_no_source_bias_phrase(self):
        src = self._cc()
        self.assertNotIn("Opponents may challenge the source's bias", src)
        self.assertNotIn("source’s bias", src)

    def test_no_pair_it_with_impact_card(self):
        src = self._cc()
        self.assertNotIn("an impact card, so you have both the link and why it matters", src)

    def test_direct_support_why_uses_explicitly_establishes(self):
        src = self._cc()
        self.assertIn("explicitly establishes", src)

    def test_crossfire_answer_direct_reads_aloud(self):
        src = self._cc()
        self.assertIn("Read the highlighted sentence aloud", src)

    def test_best_pairing_direct_references_link(self):
        src = self._cc()
        self.assertIn("your link card establishes the connection", src)

    def test_opponent_response_direct_references_scope(self):
        src = self._cc()
        self.assertIn("resolution's scope", src)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Backend: source_title incorporated into why_this_card
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceTitleInWhyThisCard(unittest.TestCase):

    def test_source_why_dict_present(self):
        src = _backend("card_cutting.py")
        self.assertIn("_source_why", src)

    def test_src_short_built_from_source_title(self):
        src = _backend("card_cutting.py")
        self.assertIn("src_short = source_title[:48]", src)

    def test_source_title_condition_checked(self):
        src = _backend("card_cutting.py")
        self.assertIn("elif source_title and evidence_role not in", src)

    def test_derive_card_intelligence_uses_source_title_param(self):
        src = _backend("card_cutting.py")
        self.assertIn("source_title: str", src)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Backend: claim text embedded in opponent_response
# ─────────────────────────────────────────────────────────────────────────────

class TestClaimSpecificOpponentResponse(unittest.TestCase):

    def test_claim_short_built_for_opponent_response(self):
        src = _backend("card_cutting.py")
        self.assertIn("_claim_short", src)

    def test_opponent_response_direct_references_claim_phrase(self):
        src = _backend("card_cutting.py")
        self.assertIn("resolution's scope for", src)

    def test_opponent_response_impact_mentions_weighing_dimensions(self):
        src = _backend("card_cutting.py")
        self.assertIn("magnitude,", src)
        self.assertIn("probability,", src)
        self.assertIn("timeframe", src)


if __name__ == "__main__":
    unittest.main()
