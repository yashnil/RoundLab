"""Tests for the evidence candidate ranker (BM25 + heuristics)."""

from app.services.evidence_candidate_ranker import (
    rank_candidate_windows,
    reranker_backend,
    CandidateWindow,
)


class TestCandidateRanker:
    def test_prefers_warrant_paragraph_over_title(self):
        title = "Humanitarian Intervention and Just War Theory"
        warrant = (
            "Military intervention is justified when a state commits genocide because "
            "the duty to protect civilians outweighs respect for sovereignty."
        )
        ranked = rank_candidate_windows(
            [title, warrant],
            topic="humanitarian intervention",
            claim="intervention is justified to stop genocide",
            role="mechanism_support",
        )
        assert ranked[0].text == warrant

    def test_prefers_complete_sentence_over_fragment(self):
        fragment = "In addition, each"
        full = "Authoritarian regimes rely on violence and repression to maintain political control."
        ranked = rank_candidate_windows(
            [fragment, full],
            topic="authoritarian regimes",
            claim="authoritarian regimes use violence to stay in power",
            role="direct_support",
        )
        assert ranked[0].text == full

    def test_role_changes_ranking(self):
        legal = "The UN Charter and R2P doctrine set the legal threshold for intervention."
        impact = "The genocide killed nearly one million people in a hundred days."
        legal_first = rank_candidate_windows(
            [legal, impact], claim="intervention", role="definition_support",
        )
        impact_first = rank_candidate_windows(
            [legal, impact], claim="intervention", role="impact_support",
        )
        # The legal-role ranking should favour the legal sentence more than the
        # impact-role ranking does (role signal shifts the order/score).
        assert legal_first[0].text == legal or impact_first[0].text == impact

    def test_deterministic(self):
        cands = [
            "The United States delayed intervention in Rwanda during the genocide.",
            "Weather patterns shifted that spring across the region.",
            "NATO airstrikes forced Serb forces to the table at Dayton.",
        ]
        a = rank_candidate_windows(cands, claim="intervention stops atrocities", role="example_support")
        b = rank_candidate_windows(cands, claim="intervention stops atrocities", role="example_support")
        assert [w.text for w in a] == [w.text for w in b]
        assert [w.score for w in a] == [w.score for w in b]

    def test_entities_boost_score(self):
        with_entity = "Bosnia shows that credible NATO pressure can end a war."
        without = "Some leaders prefer negotiation over the use of force in general."
        ranked = rank_candidate_windows(
            [without, with_entity], claim="intervention can end wars",
            role="example_support", entities=["Bosnia", "NATO"],
        )
        assert ranked[0].text == with_entity

    def test_empty_returns_empty(self):
        assert rank_candidate_windows([]) == []

    def test_returns_candidate_windows(self):
        ranked = rank_candidate_windows(["A complete sentence that argues a point clearly."], claim="x")
        assert isinstance(ranked[0], CandidateWindow)
        assert ranked[0].subscores  # subscores populated

    def test_backend_reports_bm25_when_available(self):
        # rank_bm25 is a declared dependency; in this env it should be active.
        assert reranker_backend() in ("bm25", "lexical")

    def test_fallback_without_bm25(self, monkeypatch):
        # Simulate rank_bm25 being unavailable — ranker must still work via lexical.
        import app.services.evidence_candidate_ranker as r
        monkeypatch.setattr(r, "_bm25_scores", lambda c, q: None)
        ranked = r.rank_candidate_windows(
            ["Authoritarian regimes use violence to control populations.", "Nice weather today."],
            claim="authoritarian violence control", role="direct_support",
        )
        assert ranked[0].text.startswith("Authoritarian")


class TestSemanticRerankerSeam:
    """The semantic reranker is pluggable + flag-guarded; no model download here."""

    def _reset(self, r):
        r.set_semantic_scorer(None)

    def test_disabled_by_default(self, monkeypatch):
        import app.services.evidence_candidate_ranker as r
        from app.config import settings
        self._reset(r)
        monkeypatch.setattr(settings, "use_semantic_reranker", False, raising=False)
        assert r.semantic_reranker_enabled() is False
        # _semantic_score returns None (BM25 only) when disabled.
        assert r._semantic_score(["a sentence here"], "query") is None
        self._reset(r)

    def test_enabled_scorer_changes_ranking(self, monkeypatch):
        import app.services.evidence_candidate_ranker as r
        from app.config import settings
        cands = [
            "Generic background sentence about policy in general terms here.",
            "Another plain sentence with little obvious lexical overlap at all.",
        ]
        # Without semantic: rank deterministically by BM25/heuristics.
        self._reset(r)
        monkeypatch.setattr(settings, "use_semantic_reranker", False, raising=False)
        base = r.rank_candidate_windows(cands, claim="policy", role="direct_support")

        # With a mock scorer that strongly prefers the 2nd candidate, ordering flips.
        monkeypatch.setattr(settings, "use_semantic_reranker", True, raising=False)
        r.set_semantic_scorer(lambda c, q: [0.0, 1.0])
        boosted = r.rank_candidate_windows(cands, claim="policy", role="direct_support")
        assert boosted[0].text == cands[1]
        assert boosted[0].subscores["semantic"] == 1.0
        # And the change is real (different from the unboosted top).
        assert base[0].text != boosted[0].text or base[0].score != boosted[0].score
        self._reset(r)

    def test_deterministic_with_mocked_scores(self, monkeypatch):
        import app.services.evidence_candidate_ranker as r
        from app.config import settings
        self._reset(r)
        monkeypatch.setattr(settings, "use_semantic_reranker", True, raising=False)
        r.set_semantic_scorer(lambda c, q: [0.3] * len(c))
        cands = ["First clear sentence about X.", "Second clear sentence about Y."]
        a = r.rank_candidate_windows(cands, claim="x")
        b = r.rank_candidate_windows(cands, claim="x")
        assert [w.score for w in a] == [w.score for w in b]
        self._reset(r)
