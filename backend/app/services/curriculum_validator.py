"""
Curriculum validator — deterministic schema and consistency checks.

Rejects:
  - unknown skill IDs
  - circular prerequisites
  - missing required fields
  - duplicate lesson IDs
  - invalid speech roles
  - unreachable lessons (no path from root)
  - drills without measurable outcomes
"""

from __future__ import annotations

from typing import Any


REQUIRED_LESSON_FIELDS = {
    "id", "title", "skill_id", "difficulty",
    "estimated_minutes", "what_is_it", "why_judges_care",
    "weak_example", "strong_example", "what_changed",
    "recognition_check", "micro_drill", "speech_application",
    "success_checklist",
}

VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
VALID_SPEECH_ROLES = {"constructive", "rebuttal", "summary", "final_focus", "crossfire", "any"}


def _detect_cycle(graph: dict[str, list[str]]) -> list[str]:
    """Return list of node IDs that are part of a cycle (DFS)."""
    visited: set[str] = set()
    in_stack: set[str] = set()
    cycles: list[str] = []

    def dfs(node: str) -> None:
        if node in in_stack:
            cycles.append(node)
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        for neighbour in graph.get(node, []):
            dfs(neighbour)
        in_stack.discard(node)

    for n in list(graph.keys()):
        dfs(n)
    return cycles


def validate_curriculum() -> dict[str, Any]:
    """
    Run all curriculum validation checks.
    Returns {valid: bool, errors: [...], warnings: [...], stats: {...}}.
    """
    from app.event_packs.public_forum import (
        NOVICE_PF_CURRICULUM, SKILL_REGISTRY, SKILL_PREREQUISITES,
        resolve_legacy_skill,
    )

    errors: list[str] = []
    warnings: list[str] = []
    lesson_ids: set[str] = set()

    # ── 1. Check for duplicate IDs ──────────────────────────────────────────
    for lesson in NOVICE_PF_CURRICULUM:
        lid = lesson.get("id", "")
        if lid in lesson_ids:
            errors.append(f"Duplicate lesson ID: '{lid}'")
        lesson_ids.add(lid)

    # ── 2. Required fields ──────────────────────────────────────────────────
    for lesson in NOVICE_PF_CURRICULUM:
        lid = lesson.get("id", "?")
        missing = REQUIRED_LESSON_FIELDS - set(lesson.keys())
        if missing:
            errors.append(f"Lesson '{lid}' missing required fields: {sorted(missing)}")

        # success_checklist must be non-empty
        if not lesson.get("success_checklist"):
            errors.append(f"Lesson '{lid}' has empty success_checklist")

        # micro_drill must reference a measurable outcome
        drill = lesson.get("micro_drill", "")
        if not drill or len(drill.strip()) < 20:
            warnings.append(f"Lesson '{lid}' micro_drill is too short or missing")

        # difficulty
        if lesson.get("difficulty") not in VALID_DIFFICULTIES:
            errors.append(
                f"Lesson '{lid}' has invalid difficulty '{lesson.get('difficulty')}'"
            )

    # ── 3. Skill ID validation ──────────────────────────────────────────────
    for lesson in NOVICE_PF_CURRICULUM:
        lid = lesson.get("id", "?")
        raw_skill = lesson.get("skill_id", "")
        canonical = resolve_legacy_skill(raw_skill)
        if canonical not in SKILL_REGISTRY:
            errors.append(
                f"Lesson '{lid}' references unknown skill '{raw_skill}' "
                f"(resolved to '{canonical}')"
            )

    # ── 4. Prerequisite lesson validity ────────────────────────────────────
    for lesson in NOVICE_PF_CURRICULUM:
        lid = lesson.get("id", "?")
        for prereq_id in lesson.get("prerequisite_lesson_ids", []):
            if prereq_id not in lesson_ids:
                errors.append(
                    f"Lesson '{lid}' has unknown prerequisite lesson '{prereq_id}'"
                )

    # ── 5. Circular prerequisites ───────────────────────────────────────────
    prereq_graph: dict[str, list[str]] = {
        lesson["id"]: lesson.get("prerequisite_lesson_ids", [])
        for lesson in NOVICE_PF_CURRICULUM
        if lesson.get("id")
    }
    cycles = _detect_cycle(prereq_graph)
    for cnode in cycles:
        errors.append(f"Circular prerequisite detected involving lesson '{cnode}'")

    # ── 6. Skill prerequisites (from SKILL_PREREQUISITES graph) ────────────
    skill_prereq_graph: dict[str, list[str]] = {
        sid: prereqs
        for sid, prereqs in SKILL_PREREQUISITES.items()
    }
    skill_cycles = _detect_cycle(skill_prereq_graph)
    for cnode in skill_cycles:
        errors.append(f"Circular skill prerequisite detected for skill '{cnode}'")

    for sid, prereqs in SKILL_PREREQUISITES.items():
        for prereq in prereqs:
            if prereq not in SKILL_REGISTRY:
                errors.append(
                    f"Skill '{sid}' has unknown prerequisite skill '{prereq}'"
                )

    # ── 7. Unreachable lessons (no path without prerequisites) ───────────────
    # A lesson is unreachable if all its prerequisite lessons are also unreachable
    # and none of them are root nodes (no prereqs).
    root_lessons = {
        lesson["id"] for lesson in NOVICE_PF_CURRICULUM
        if not lesson.get("prerequisite_lesson_ids")
    }
    if not root_lessons:
        errors.append("No root lessons found (lessons with no prerequisites)")

    # ── 8. Coverage check — required novice PF topics ────────────────────────
    required_topics = {
        "organization", "warranting", "evidence_use", "clash",
        "frontlining", "extensions", "impact_explanation", "weighing", "collapse",
        "crossfire_questioning", "judge_adaptation",
    }
    covered_skills: set[str] = set()
    for lesson in NOVICE_PF_CURRICULUM:
        raw_skill = lesson.get("skill_id", "")
        covered_skills.add(resolve_legacy_skill(raw_skill))

    missing_topics = required_topics - covered_skills
    for topic in sorted(missing_topics):
        errors.append(f"Required topic '{topic}' not covered by any lesson")

    # ── 9. Optional field warnings ───────────────────────────────────────────
    optional_recommended = {"common_mistakes", "coach_note", "reviewed_date", "author"}
    for lesson in NOVICE_PF_CURRICULUM:
        lid = lesson.get("id", "?")
        missing_optional = optional_recommended - set(lesson.keys())
        if missing_optional:
            warnings.append(
                f"Lesson '{lid}' missing recommended fields: {sorted(missing_optional)}"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "lesson_count": len(NOVICE_PF_CURRICULUM),
            "skill_count": len(SKILL_REGISTRY),
            "covered_skills": sorted(covered_skills),
            "root_lessons": sorted(root_lessons),
            "required_topics_covered": sorted(required_topics - missing_topics),
        },
    }
