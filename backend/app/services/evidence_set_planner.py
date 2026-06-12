"""Evidence Set Planner — plans up to 5 strategically distinct evidence cards.

Given a topic + claim + side, produces an EvidenceSetPlan describing the distinct
strategic "slots" an evidence set should fill (legal warrant, moral warrant,
historical example, impact, threshold, etc.). Each slot carries a narrower
target_claim and search guidance.

The deterministic path uses keyword detection to choose a template and never
requires an LLM. The LLM path (gpt-4o-mini, structured output) produces a
topic-tailored plan but always degrades gracefully to the deterministic plan.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────────────────────────

class EvidenceSlot(BaseModel):
    slot_id: str
    slot_label: str
    strategic_function: str
    target_claim: str
    desired_evidence_role: str
    search_intent: str
    preferred_source_types: list[str] = Field(default_factory=list)
    recency_policy: str = "any"  # "prefer_recent" | "any" | "historical_ok"
    must_have_terms: list[str] = Field(default_factory=list)
    helpful_terms: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)
    success_criteria: str = ""


class EvidenceSetPlan(BaseModel):
    topic: str
    claim: str
    side: str
    slots: list[EvidenceSlot] = Field(default_factory=list)
    planning_method: str = "deterministic"  # "llm" | "deterministic"


# ── Keyword templates for deterministic detection ─────────────────────────────

_INTERVENTION_KEYWORDS = (
    "military", "force", "intervention", "intervene", "authoritarian", "regime",
    "human rights abuses", "atrocities", "atrocity", "genocide", "sovereignty",
    "humanitarian", "r2p", "responsibility to protect", "war crimes",
)

_SECTION_230_KEYWORDS = (
    "section 230", "platform", "liability", "internet law", "content moderation",
    "social media", "intermediary", "immunity", "user-generated", "user generated",
)


def _detect_template(topic: str, claim: str) -> str:
    """Return one of 'intervention' | 'section_230' | 'generic'."""
    blob = f"{topic} {claim}".lower()
    if any(kw in blob for kw in _SECTION_230_KEYWORDS):
        return "section_230"
    if any(kw in blob for kw in _INTERVENTION_KEYWORDS):
        return "intervention"
    return "generic"


# ── Deterministic templates ───────────────────────────────────────────────────

def _intervention_slots(claim: str) -> list[EvidenceSlot]:
    return [
        EvidenceSlot(
            slot_id="legal_warrant",
            slot_label="Legal/Doctrinal Warrant",
            strategic_function="legal/doctrinal support",
            target_claim="International law permits the use of force to stop mass atrocities (R2P, UN Security Council authorization).",
            desired_evidence_role="authority_support",
            search_intent="Find legal or doctrinal sources establishing that international law (R2P, UNSC, UN Charter) permits intervention against mass atrocities.",
            preferred_source_types=["legal", "academic", "intergovernmental"],
            recency_policy="any",
            must_have_terms=["international law", "intervention"],
            helpful_terms=["responsibility to protect", "R2P", "UN Security Council", "sovereignty"],
            avoid_terms=["opinion", "editorial"],
            success_criteria="A legal or doctrinal source that explicitly grounds intervention in international law.",
        ),
        EvidenceSlot(
            slot_id="moral_warrant",
            slot_label="Moral/Philosophical Warrant",
            strategic_function="moral/philosophical warrant",
            target_claim="Severe human rights abuses can morally override a state's claim to sovereignty.",
            desired_evidence_role="mechanism_support",
            search_intent="Find ethics or philosophy sources arguing that gross human rights violations override sovereignty and justify intervention.",
            preferred_source_types=["academic", "think_tank"],
            recency_policy="any",
            must_have_terms=["sovereignty", "human rights"],
            helpful_terms=["ethics", "moral", "just war", "humanitarian"],
            avoid_terms=[],
            success_criteria="A philosophical or ethical argument that abuses can override sovereignty.",
        ),
        EvidenceSlot(
            slot_id="historical_example",
            slot_label="Historical Example",
            strategic_function="historical example",
            target_claim="Past interventions (Kosovo, Bosnia) or failures to intervene (Rwanda) illustrate the stakes.",
            desired_evidence_role="example_support",
            search_intent="Find a historical case study of intervention (Kosovo, Bosnia) or non-intervention (Rwanda) as a precedent.",
            preferred_source_types=["academic", "news", "think_tank"],
            recency_policy="historical_ok",
            must_have_terms=["intervention"],
            helpful_terms=["Kosovo", "Bosnia", "Rwanda", "genocide", "NATO"],
            avoid_terms=[],
            success_criteria="A concrete historical case that supports the argument with specifics.",
        ),
        EvidenceSlot(
            slot_id="impact",
            slot_label="Empirical Impact/Stakes",
            strategic_function="empirical impact/stakes",
            target_claim="Non-intervention enables mass atrocities, genocide, and large-scale civilian death.",
            desired_evidence_role="impact_support",
            search_intent="Find research or think-tank data on the human cost of non-intervention: civilian deaths, displacement, genocide.",
            preferred_source_types=["think_tank", "academic", "intergovernmental"],
            recency_policy="prefer_recent",
            must_have_terms=["civilian", "deaths"],
            helpful_terms=["genocide", "displacement", "atrocities", "casualties"],
            avoid_terms=[],
            success_criteria="A quantified or authoritative statement of the harm of inaction.",
        ),
        EvidenceSlot(
            slot_id="threshold",
            slot_label="Threshold/Limitation",
            strategic_function="answer to objection",
            target_claim="Intervention is justified only under conditions: last resort, proportionality, multilateral authorization.",
            desired_evidence_role="definition_support",
            search_intent="Find sources establishing the conditions or thresholds for legitimate intervention (last resort, proportionality, multilateral).",
            preferred_source_types=["academic", "intergovernmental", "humanitarian"],
            recency_policy="any",
            must_have_terms=["intervention", "conditions"],
            helpful_terms=["last resort", "proportionality", "multilateral", "just war"],
            avoid_terms=[],
            success_criteria="A source naming the conditions that make intervention legitimate.",
        ),
    ]


def _section_230_slots(claim: str) -> list[EvidenceSlot]:
    return [
        EvidenceSlot(
            slot_id="definition",
            slot_label="Definition/Background",
            strategic_function="definition/background",
            target_claim="Section 230 provides legal immunity to online platforms for third-party content.",
            desired_evidence_role="definition_support",
            search_intent="Find a source defining what Section 230 of the Communications Decency Act legally provides.",
            preferred_source_types=["legal", "academic", "government"],
            recency_policy="any",
            must_have_terms=["Section 230"],
            helpful_terms=["Communications Decency Act", "immunity", "47 U.S.C."],
            avoid_terms=[],
            success_criteria="A clear legal definition of Section 230's protections.",
        ),
        EvidenceSlot(
            slot_id="mechanism",
            slot_label="Mechanism/Warrant",
            strategic_function="mechanism/warrant",
            target_claim="Section 230 shields platforms from liability for content posted by their users.",
            desired_evidence_role="mechanism_support",
            search_intent="Find a source explaining HOW Section 230 shields platforms from liability for user content.",
            preferred_source_types=["legal", "academic"],
            recency_policy="any",
            must_have_terms=["Section 230", "liability"],
            helpful_terms=["shield", "immunity", "platform", "user content"],
            avoid_terms=[],
            success_criteria="A source describing the mechanism of immunity.",
        ),
        EvidenceSlot(
            slot_id="example",
            slot_label="Historical Example",
            strategic_function="historical example",
            target_claim="Courts have used Section 230 to dismiss suits against platforms (e.g., Backpage, Zeran).",
            desired_evidence_role="example_support",
            search_intent="Find a specific court case where a platform invoked Section 230 immunity successfully.",
            preferred_source_types=["legal", "news"],
            recency_policy="historical_ok",
            must_have_terms=["Section 230"],
            helpful_terms=["court", "ruling", "Backpage", "Zeran", "lawsuit"],
            avoid_terms=[],
            success_criteria="A concrete case where Section 230 immunity was applied.",
        ),
        EvidenceSlot(
            slot_id="impact",
            slot_label="Empirical Impact/Stakes",
            strategic_function="empirical impact/stakes",
            target_claim="Section 230 immunity enables real-world harms that go unremedied.",
            desired_evidence_role="impact_support",
            search_intent="Find research on harms enabled by Section 230 immunity (e.g., unremedied abuse, disinformation).",
            preferred_source_types=["academic", "think_tank", "news"],
            recency_policy="prefer_recent",
            must_have_terms=["Section 230"],
            helpful_terms=["harm", "victims", "accountability", "disinformation"],
            avoid_terms=[],
            success_criteria="Evidence of concrete harm enabled by the immunity.",
        ),
        EvidenceSlot(
            slot_id="counter",
            slot_label="Answer to Objection",
            strategic_function="answer to objection",
            target_claim="Section 230 also produces benefits (free expression, small-platform viability).",
            desired_evidence_role="counter_evidence",
            search_intent="Find sources describing benefits of Section 230, to pre-empt and answer opponent arguments.",
            preferred_source_types=["academic", "think_tank"],
            recency_policy="any",
            must_have_terms=["Section 230"],
            helpful_terms=["free speech", "innovation", "benefits", "expression"],
            avoid_terms=[],
            success_criteria="A source articulating Section 230's benefits for the pre-empt block.",
        ),
    ]


def _generic_slots(topic: str, claim: str) -> list[EvidenceSlot]:
    claim_short = (claim or topic or "the claim").strip()
    claim_lower = claim_short.lower()
    return [
        EvidenceSlot(
            slot_id="direct",
            slot_label="Direct Support",
            strategic_function="direct support",
            target_claim=claim_short,
            desired_evidence_role="direct_support",
            search_intent=f"Find a source that directly states: {claim_short}.",
            preferred_source_types=["academic", "news", "think_tank"],
            recency_policy="prefer_recent",
            must_have_terms=[],
            helpful_terms=[],
            avoid_terms=[],
            success_criteria="A source that directly asserts the claim.",
        ),
        EvidenceSlot(
            slot_id="mechanism",
            slot_label="Mechanism/Warrant",
            strategic_function="mechanism/warrant",
            target_claim=f"The mechanism by which {claim_lower}.",
            desired_evidence_role="mechanism_support",
            search_intent=f"Find a source explaining HOW or WHY {claim_lower}.",
            preferred_source_types=["academic", "think_tank"],
            recency_policy="any",
            must_have_terms=[],
            helpful_terms=["because", "mechanism", "causes", "leads to"],
            avoid_terms=[],
            success_criteria="A source explaining the causal mechanism.",
        ),
        EvidenceSlot(
            slot_id="example",
            slot_label="Historical Example",
            strategic_function="historical example",
            target_claim=f"A real case or precedent supporting that {claim_lower}.",
            desired_evidence_role="example_support",
            search_intent=f"Find a real-world case, example, or precedent supporting {claim_lower}.",
            preferred_source_types=["news", "academic"],
            recency_policy="historical_ok",
            must_have_terms=[],
            helpful_terms=["case", "example", "precedent", "instance"],
            avoid_terms=[],
            success_criteria="A concrete example backing the claim.",
        ),
        EvidenceSlot(
            slot_id="impact",
            slot_label="Empirical Impact/Stakes",
            strategic_function="empirical impact/stakes",
            target_claim=f"The stakes or consequences of {claim_lower}.",
            desired_evidence_role="impact_support",
            search_intent=f"Find data on the impact, stakes, or consequences related to {claim_lower}.",
            preferred_source_types=["think_tank", "academic"],
            recency_policy="prefer_recent",
            must_have_terms=[],
            helpful_terms=["impact", "consequence", "cost", "billion", "percent"],
            avoid_terms=[],
            success_criteria="A quantified or authoritative statement of stakes.",
        ),
        EvidenceSlot(
            slot_id="authority",
            slot_label="Authority/Expert Backing",
            strategic_function="authority/credibility support",
            target_claim=f"Expert or institutional backing for {claim_lower}.",
            desired_evidence_role="authority_support",
            search_intent=f"Find an expert, institution, or peer-reviewed source backing {claim_lower}.",
            preferred_source_types=["academic", "government", "think_tank"],
            recency_policy="any",
            must_have_terms=[],
            helpful_terms=["according to", "study", "report", "expert"],
            avoid_terms=[],
            success_criteria="A credible authority endorsing the claim.",
        ),
    ]


def _deterministic_plan(topic: str, claim: str, side: str) -> EvidenceSetPlan:
    template = _detect_template(topic, claim)
    if template == "intervention":
        slots = _intervention_slots(claim)
    elif template == "section_230":
        slots = _section_230_slots(claim)
    else:
        slots = _generic_slots(topic, claim)
    return EvidenceSetPlan(
        topic=topic, claim=claim, side=side,
        slots=slots[:5], planning_method="deterministic",
    )


# ── LLM planning ──────────────────────────────────────────────────────────────

class _LLMSlot(BaseModel):
    slot_id: str
    slot_label: str
    strategic_function: str
    target_claim: str
    desired_evidence_role: str
    search_intent: str
    preferred_source_types: list[str] = []
    recency_policy: str = "any"
    must_have_terms: list[str] = []
    helpful_terms: list[str] = []
    avoid_terms: list[str] = []
    success_criteria: str = ""


class _LLMPlanOutput(BaseModel):
    slots: list[_LLMSlot] = []


_VALID_ROLES = {
    "direct_support", "mechanism_support", "example_support", "impact_support",
    "definition_support", "authority_support", "counter_evidence",
}


def _plan_with_llm(topic: str, claim: str, side: str) -> Optional[EvidenceSetPlan]:
    try:
        from openai import OpenAI

        client = OpenAI()
        prompt = (
            f"Topic: {topic}\n"
            f"Claim to support: {claim}\n"
            f"Side: {side or 'not specified'}\n\n"
            "Plan up to 5 strategically DISTINCT evidence cards. Each slot must have:\n"
            "- a distinct strategic_function (e.g. direct support, legal/doctrinal support, "
            "moral/philosophical warrant, mechanism/warrant, historical example, "
            "empirical impact/stakes, answer to objection, definition/background)\n"
            "- a target_claim NARROWER and more specific than the full claim\n"
            "- a distinct search_intent (no two identical)\n"
            "- a desired_evidence_role from: direct_support, mechanism_support, example_support, "
            "impact_support, definition_support, authority_support, counter_evidence\n"
            "Return 3-5 slots."
        )
        resp = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert PF debate coach. Given a topic and claim, "
                        "plan up to 5 strategically distinct evidence cards."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=_LLMPlanOutput,
            temperature=0,
        )
        parsed = resp.choices[0].message.parsed
        if not parsed or not parsed.slots:
            return None

        slots: list[EvidenceSlot] = []
        seen_intents: set[str] = set()
        for s in parsed.slots[:5]:
            role = s.desired_evidence_role if s.desired_evidence_role in _VALID_ROLES else "direct_support"
            intent_key = s.search_intent.strip().lower()
            if intent_key and intent_key in seen_intents:
                continue
            seen_intents.add(intent_key)
            slots.append(EvidenceSlot(
                slot_id=s.slot_id or f"slot_{len(slots) + 1}",
                slot_label=s.slot_label or "Evidence",
                strategic_function=s.strategic_function or "direct support",
                target_claim=s.target_claim or claim,
                desired_evidence_role=role,
                search_intent=s.search_intent or claim,
                preferred_source_types=s.preferred_source_types,
                recency_policy=(
                    s.recency_policy
                    if s.recency_policy in ("prefer_recent", "any", "historical_ok")
                    else "any"
                ),
                must_have_terms=s.must_have_terms,
                helpful_terms=s.helpful_terms,
                avoid_terms=s.avoid_terms,
                success_criteria=s.success_criteria,
            ))
        if len(slots) < 3:
            return None
        return EvidenceSetPlan(
            topic=topic, claim=claim, side=side, slots=slots, planning_method="llm",
        )
    except Exception as exc:
        logger.debug("Evidence set LLM planning failed: %s", exc)
        return None


# ── Per-slot query generation ─────────────────────────────────────────────────

import re as _re

_QUERY_STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "will", "been", "they",
    "their", "there", "when", "would", "could", "should", "about",
    "than", "more", "into", "over", "such", "each", "also", "very",
    "just", "some", "what", "which", "where", "while", "these", "those",
    "then", "were", "does", "find", "sources", "source", "document",
    "establishing", "argues", "argue", "arguing", "stating", "states",
    "historical", "provides", "sources", "research", "study", "studies",
})

# Role-specific framing suffix for structural Q3.
_ROLE_FRAME: dict[str, str] = {
    "direct_support": "evidence report",
    "mechanism_support": "mechanism how works",
    "example_support": "case study historical precedent",
    "impact_support": "impact data consequences",
    "definition_support": "definition criteria conditions",
    "authority_support": "doctrine authorization expert",
    "counter_evidence": "objection argument against",
}


def _key_tokens(text: str, limit: int = 6) -> list[str]:
    """Extract the most informative tokens from text for query building."""
    tokens = [
        w for w in _re.sub(r"[^\w\s]", " ", text.lower()).split()
        if len(w) > 3 and w not in _QUERY_STOPWORDS
    ]
    # Longer tokens tend to be more specific — prefer them
    tokens.sort(key=len, reverse=True)
    return tokens[:limit]


def build_slot_queries(slot: EvidenceSlot, topic: str, claim: str, n: int = 4) -> list[str]:
    """Generate up to n keyword-style search queries targeted at one evidence slot.

    Builds proper keyword queries (not verbose descriptions) by combining:
    - slot.helpful_terms (the most slot-specific vocabulary)
    - slot.must_have_terms (required concepts)
    - key tokens from slot.target_claim and claim
    - topic
    - role-appropriate framing words

    Query design mirrors what a skilled debater would type into Google.
    """
    helpful = slot.helpful_terms or []
    must = slot.must_have_terms or []
    topic_str = (topic or "").strip()
    claim_kw = _key_tokens(claim, limit=6)
    target_kw = _key_tokens(slot.target_claim, limit=7)
    role_frame = _ROLE_FRAME.get(slot.desired_evidence_role, "evidence")

    queries: list[str] = []

    # Q1: helpful[0..1] + topic + claim_kw[:3]
    # "responsibility to protect R2P humanitarian intervention morally legally justified"
    if helpful:
        parts = list(helpful[:2]) + [topic_str] + claim_kw[:3]
        queries.append(_re.sub(r"\s+", " ", " ".join(parts)).strip())
    else:
        parts = target_kw[:4] + [topic_str]
        queries.append(_re.sub(r"\s+", " ", " ".join(parts)).strip())

    # Q2: helpful[2..3] + topic + claim_kw[2:5] (different helpful terms set)
    # "UN Security Council sovereignty humanitarian intervention severe human rights"
    if len(helpful) >= 3:
        parts = list(helpful[2:4]) + [topic_str] + claim_kw[2:5]
        q = _re.sub(r"\s+", " ", " ".join(parts)).strip()
        if q.lower() not in {x.lower() for x in queries}:
            queries.append(q)
    elif target_kw:
        # Fallback: target tokens + claim tokens
        parts = target_kw[:3] + claim_kw[1:4]
        q = _re.sub(r"\s+", " ", " ".join(parts) + " " + topic_str).strip()
        if q.lower() not in {x.lower() for x in queries}:
            queries.append(q)

    # Q3: must_have terms + role_frame + claim_kw[:3]
    # "international law intervention legal doctrine morally justified"
    must_str = " ".join(must[:2]) if must else topic_str[:40]
    parts = [must_str, role_frame] + claim_kw[:3]
    q = _re.sub(r"\s+", " ", " ".join(parts)).strip()
    if q.lower() not in {x.lower() for x in queries} and len(q) > 10:
        queries.append(q)

    # Q4: helpful[0] + target_kw[:4] (slot target framing)
    # "responsibility to protect force mass atrocities international permits"
    if helpful:
        parts = [helpful[0]] + target_kw[:4]
    else:
        parts = target_kw[:5] + (must[:1] if must else [])
    q = _re.sub(r"\s+", " ", " ".join(parts)).strip()
    if q.lower() not in {x.lower() for x in queries}:
        queries.append(q)

    # Q5: topic + helpful[1..2] + claim_kw[1:4]
    # "humanitarian intervention R2P UN Security Council legally justified abuses"
    if len(helpful) >= 2:
        parts = [topic_str] + list(helpful[1:3]) + claim_kw[1:4]
        q = _re.sub(r"\s+", " ", " ".join(parts)).strip()
        if q.lower() not in {x.lower() for x in queries}:
            queries.append(q)

    # Q6: must_have + helpful[0] + topic (role-anchored)
    # "international law responsibility to protect humanitarian intervention"
    if must and helpful:
        parts = must[:2] + [helpful[0]] + [topic_str]
        q = _re.sub(r"\s+", " ", " ".join(parts)).strip()
        if q.lower() not in {x.lower() for x in queries}:
            queries.append(q)
    elif must:
        parts = must[:2] + [topic_str] + [role_frame]
        q = _re.sub(r"\s+", " ", " ".join(parts)).strip()
        if q.lower() not in {x.lower() for x in queries}:
            queries.append(q)

    # Deduplicate and cap; skip very short or empty queries
    seen: set[str] = set()
    result: list[str] = []
    for q in queries:
        q_clean = _re.sub(r"\s+", " ", q).strip()
        if q_clean and q_clean.lower() not in seen and len(q_clean) > 10:
            seen.add(q_clean.lower())
            result.append(q_clean)

    return result[:n]


# ── Backup queries for second-pass search ────────────────────────────────────

# Slot-specific backup query templates (used when first-pass fails to fill a slot)
_SLOT_BACKUP_QUERIES: dict[str, list[str]] = {
    "legal_warrant": [
        "international law humanitarian intervention legal authorization",
        "UN Charter Chapter VII force authorized human rights abuses",
        "ICISS Responsibility to Protect R2P legal doctrine",
        "customary international law right to intervene genocide",
    ],
    "moral_warrant": [
        "just war theory moral obligation protect civilians humanitarian",
        "ethics humanitarian intervention moral philosophy civilian casualties",
        "sovereignty versus responsibility to protect moral argument",
        "moral case military intervention authoritarian human rights",
    ],
    "historical_example": [
        "Kosovo NATO intervention 1999 outcome success humanitarian",
        "Bosnia humanitarian intervention ethnic cleansing Srebrenica",
        "Rwanda genocide 1994 failure to intervene lessons",
        "Libya 2011 humanitarian intervention outcomes",
    ],
    "impact": [
        "humanitarian intervention prevents genocide mass atrocities statistics",
        "civilian protection military force outcomes data evidence",
        "genocide prevention intervention effectiveness research",
        "mass atrocities human rights violations scale impact report",
    ],
    "threshold": [
        "humanitarian intervention last resort proportionality conditions",
        "multilateral legitimacy threshold armed intervention criteria",
        "just war proportionality reasonable chance success intervention",
        "when is humanitarian intervention justified criteria doctrine",
    ],
}


def build_backup_slot_queries(slot: "EvidenceSlot", topic: str, claim: str) -> list[str]:
    """Return backup queries for a slot that failed to fill on first pass.

    Uses slot_id-based templates augmented with the topic/claim keywords.
    """
    slot_id = getattr(slot, "slot_id", "")
    slot_label = (getattr(slot, "slot_label", "") or "").lower()

    # Try to match by slot_id or keywords in slot_label
    backup_key = None
    for key in _SLOT_BACKUP_QUERIES:
        if key in slot_id.lower() or key.replace("_", " ") in slot_label:
            backup_key = key
            break
    if backup_key is None:
        # Fallback: match by role
        role = getattr(slot, "desired_evidence_role", "") or ""
        if "legal" in role or "authority" in role:
            backup_key = "legal_warrant"
        elif "impact" in role:
            backup_key = "impact"
        elif "example" in role:
            backup_key = "historical_example"
        elif "definition" in role:
            backup_key = "threshold"
        else:
            backup_key = "moral_warrant"

    templates = _SLOT_BACKUP_QUERIES.get(backup_key, [])

    # Augment first two templates with topic keyword
    topic_kw = _key_tokens(topic or "", 3)
    augmented: list[str] = []
    for i, q in enumerate(templates):
        if i < 2 and topic_kw:
            q = q + " " + " ".join(topic_kw[:2])
        augmented.append(q.strip())

    return augmented[:3]


# ── Public entry point ────────────────────────────────────────────────────────

def plan_evidence_set(
    topic: str,
    claim: str,
    side: str,
    use_llm: bool = True,
) -> EvidenceSetPlan:
    """Plan up to 5 strategically distinct evidence-card slots for a claim.

    Degrades gracefully: if the LLM path fails or is disabled, returns a
    deterministic keyword-template plan.
    """
    topic = topic or ""
    claim = claim or ""
    side = side or ""
    if use_llm:
        llm_plan = _plan_with_llm(topic, claim, side)
        if llm_plan is not None:
            return llm_plan
    return _deterministic_plan(topic, claim, side)
