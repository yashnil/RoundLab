"""
Public Forum Debate event pack.

Canonical skill taxonomy, prerequisite graph, novice curriculum, and
helper functions for the Training OS.  Everything here is pure data —
no database, no LLM, no side effects.
"""

from __future__ import annotations

# ── Skill Registry ─────────────────────────────────────────────────────────────
# 28 skills across three categories.

SKILL_REGISTRY: dict[str, dict] = {

    # ── Core Communication (8) ──────────────────────────────────────────────

    "clarity": {
        "id": "clarity",
        "name": "Clarity",
        "description": "Speaking clearly enough that every judge, regardless of experience, can follow your argument.",
        "novice_explanation": "If the judge can't understand what you said, the argument doesn't count. Clarity means speaking at a pace they can follow, articulating your words fully, and avoiding mumbling.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal", "summary", "final_focus"],
        "success_criteria": [
            "Judge can transcribe your main claim without replaying the audio",
            "No run-on sentences longer than 30 words",
            "Articulation clear enough at tournament pace",
        ],
        "recommended_drills": ["slow_read", "record_and_critique", "peer_feedback"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 30, "proficient": 55, "mastery": 78,
        },
        "category": "core_communication",
        "legacy_aliases": ["delivery"],
    },

    "organization": {
        "id": "organization",
        "name": "Organization",
        "description": "Structuring your speech so a judge can easily follow and record your arguments.",
        "novice_explanation": "Organization means your speech has a roadmap, clear contention labels, transitions between arguments, and a summary at the end. Judges flow your speech — they need signposts.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal", "summary", "final_focus"],
        "success_criteria": [
            "Clear roadmap at the start of the speech",
            "Each argument has a labeled contention or numbered point",
            "Transitions connect contentions (e.g., 'moving to my second argument')",
            "Arguments are easy to distinguish from each other",
        ],
        "recommended_drills": ["roadmap_drill", "contention_labeling", "flow_practice"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "core_communication",
        "legacy_aliases": ["organization"],
    },

    "pacing": {
        "id": "pacing",
        "name": "Pacing",
        "description": "Managing your speaking speed to maximize judge comprehension and argument coverage.",
        "novice_explanation": "Pacing is about matching your speed to what the judge can absorb. Too fast and they miss arguments. Too slow and you run out of time. Good pacing means strategic slowing for key points.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal", "summary", "final_focus"],
        "success_criteria": [
            "Speed under 200 WPM for lay judges, up to 250 for flow judges",
            "Deliberately slower on claims and key impact phrases",
            "Speech fills 90-100% of allotted time",
        ],
        "recommended_drills": ["timed_read", "wpm_tracker", "pausing_drill"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "core_communication",
        "legacy_aliases": [],
    },

    "emphasis": {
        "id": "emphasis",
        "name": "Emphasis",
        "description": "Using vocal variation, pauses, and volume to highlight key arguments and impact moments.",
        "novice_explanation": "Judges remember what you stressed. Emphasis tells the judge: 'this is the key point — write this down.' It includes slowing down, raising or lowering volume, and pausing after key lines.",
        "prerequisites": [],
        "speech_roles": ["constructive", "summary", "final_focus"],
        "success_criteria": [
            "Discernible difference in vocal delivery between background and impact statements",
            "Key claims said slower than surrounding material",
            "Strategic pauses after the most important line in each contention",
        ],
        "recommended_drills": ["emphasis_marking", "vocal_range_drill", "impact_slow"],
        "mastery_thresholds": {
            "introducing": 8, "developing": 25, "proficient": 50, "mastery": 75,
        },
        "category": "core_communication",
        "legacy_aliases": [],
    },

    "confidence": {
        "id": "confidence",
        "name": "Confidence",
        "description": "Projecting authority and composure to help the judge trust your arguments.",
        "novice_explanation": "A judge who trusts the speaker is more likely to vote for them. Confidence means making eye contact, standing tall, not apologizing for arguments, and recovering calmly from mistakes.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal", "summary", "final_focus", "crossfire"],
        "success_criteria": [
            "No filler phrases ('um', 'like', 'uh') that undermine authority",
            "Eye contact with the judge for at least 60% of the speech",
            "No verbal hedging ('I think maybe this could possibly be the case')",
        ],
        "recommended_drills": ["filler_elimination", "eye_contact_drill", "stance_practice"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 30, "proficient": 55, "mastery": 78,
        },
        "category": "core_communication",
        "legacy_aliases": [],
    },

    "concision": {
        "id": "concision",
        "name": "Concision",
        "description": "Saying exactly what you need to say — no more, no less — in the time available.",
        "novice_explanation": "Every word in a debate speech costs time. Concision means eliminating verbal filler, avoiding repetition, and getting to the point. Judges reward speakers who respect their time.",
        "prerequisites": [],
        "speech_roles": ["rebuttal", "summary", "final_focus", "crossfire"],
        "success_criteria": [
            "Average sentence length under 20 words during final focus",
            "No repeated argument twice in the same speech",
            "Transitions are one sentence, not paragraphs",
        ],
        "recommended_drills": ["30_second_summary", "cut_the_fat_edit", "timed_argument"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "core_communication",
        "legacy_aliases": [],
    },

    "audience_adaptation": {
        "id": "audience_adaptation",
        "name": "Audience Adaptation",
        "description": "Adjusting your communication style based on your judge's background and preferences.",
        "novice_explanation": "A parent judge and a veteran debater need different things. Audience adaptation means reading your judge before and during the round, then adjusting your speed, vocabulary, and argument style.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal", "summary", "final_focus"],
        "success_criteria": [
            "Can identify lay vs. flow judge from paradigm or appearance",
            "Adjusts speed and jargon level within first 30 seconds",
            "Uses plain-language impact framing for lay judges",
        ],
        "recommended_drills": ["judge_paradigm_study", "register_switch_drill", "lay_round_simulation"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "core_communication",
        "legacy_aliases": [],
    },

    "evidence_explanation": {
        "id": "evidence_explanation",
        "name": "Evidence Explanation",
        "description": "Explaining what evidence says and why it proves your claim — not just reading it.",
        "novice_explanation": "Reading a card is not the same as using a card. Evidence explanation means stating what the source says, what that means in plain language, and how it proves the specific claim you made.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal"],
        "success_criteria": [
            "Every piece of evidence has a 'this means' clause after it",
            "The link between evidence and claim is stated explicitly",
            "No orphaned evidence — every card connects back to a contention",
        ],
        "recommended_drills": ["tag_read_explain", "evidence_link_drill", "so_what_drill"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "core_communication",
        "legacy_aliases": [],
    },

    # ── PF Argumentation (15) ──────────────────────────────────────────────────

    "claim_construction": {
        "id": "claim_construction",
        "name": "Claim Construction",
        "description": "Writing clear, falsifiable claims that directly advocate for your side of the resolution.",
        "novice_explanation": "A claim is the position you're asking the judge to accept. Good claims are specific ('tariffs reduce GDP by X'), not vague ('tariffs are bad'). They should be debatable — not observations.",
        "prerequisites": [],
        "speech_roles": ["constructive"],
        "success_criteria": [
            "Claims state a clear position, not a topic",
            "Claims are specific enough that the opponent can disagree",
            "Claims connect directly to the resolution",
        ],
        "recommended_drills": ["claim_writing_drill", "claim_vs_topic_sorting", "resolution_link_check"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "warranting": {
        "id": "warranting",
        "name": "Warranting",
        "description": "Providing the causal mechanism or logical reasoning that explains why a claim is true.",
        "novice_explanation": "A warrant answers 'why?' after your claim. If you say 'tariffs hurt the economy,' the warrant explains the mechanism: 'because tariffs raise import prices, which increases production costs for domestic manufacturers who rely on foreign inputs.' Without a warrant, you're just asserting.",
        "prerequisites": ["claim_construction"],
        "speech_roles": ["constructive", "rebuttal", "summary"],
        "success_criteria": [
            "Every claim has a 'because' clause that explains the mechanism",
            "Warrant is specific — names an economic, political, or social process",
            "Warrant is distinct from the claim (not circular)",
        ],
        "recommended_drills": ["warrant_writing", "claim_warrant_chain", "because_drill"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 32, "proficient": 56, "mastery": 78,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["warranting"],
    },

    "impact_explanation": {
        "id": "impact_explanation",
        "name": "Impact Explanation",
        "description": "Explaining the real-world consequence of your argument and why the judge should care.",
        "novice_explanation": "An impact is what happens if your argument is true. 'GDP falls' is a poor impact. 'GDP falls, which means 2 million Americans lose their jobs and families can't afford healthcare' is an impact. Impacts need to be vivid, specific, and tied to real human consequences.",
        "prerequisites": ["warranting"],
        "speech_roles": ["constructive", "summary", "final_focus"],
        "success_criteria": [
            "Every major argument has a real-world consequence stated",
            "Impact names specific populations or harms",
            "Impact magnitude gives a sense of scale (how many? how serious?)",
        ],
        "recommended_drills": ["impact_chain", "so_what_5x", "magnitude_drill"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "evidence_use": {
        "id": "evidence_use",
        "name": "Evidence Use",
        "description": "Selecting, citing, and deploying evidence strategically to support your arguments.",
        "novice_explanation": "Evidence use isn't just reading a card — it's picking the right card for the right argument, citing it correctly (author, year), and explaining what it proves. Good evidence use means your cards directly prove your claims.",
        "prerequisites": ["citation_quality"],
        "speech_roles": ["constructive", "rebuttal"],
        "success_criteria": [
            "Every major claim is backed by at least one cited source",
            "Evidence is cited with author last name and year",
            "The card's actual content matches the claim it supports",
        ],
        "recommended_drills": ["card_matching", "citation_speed", "evidence_audit"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 32, "proficient": 56, "mastery": 78,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["evidence_use"],
    },

    "citation_quality": {
        "id": "citation_quality",
        "name": "Citation Quality",
        "description": "Using credible, recent, and relevant sources cited with proper author and date attribution.",
        "novice_explanation": "Not all sources are equal. A peer-reviewed economics study beats a random blog. Citation quality means using credible sources, citing them with author and year, and avoiding fabricated or paraphrased-beyond-recognition evidence.",
        "prerequisites": [],
        "speech_roles": ["constructive", "rebuttal"],
        "success_criteria": [
            "No sources without a named author and year",
            "Primary sources preferred over secondary summaries when available",
            "No use of anonymous or undated web sources for factual claims",
        ],
        "recommended_drills": ["source_credibility_sort", "citation_format_drill", "source_hunting"],
        "mastery_thresholds": {
            "introducing": 8, "developing": 25, "proficient": 50, "mastery": 74,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "clash": {
        "id": "clash",
        "name": "Clash",
        "description": "Directly engaging with the opponent's arguments rather than talking past them.",
        "novice_explanation": "Clash means you know what the other team argued and you say something about it. Without clash, two teams can give perfectly good speeches and never actually debate. Clash means: 'They said X. X is wrong because Y.'",
        "prerequisites": [],
        "speech_roles": ["rebuttal", "summary"],
        "success_criteria": [
            "Directly names the opponent's argument before responding",
            "Response addresses the specific mechanism of the opponent's claim",
            "Doesn't only run new arguments — engages existing opponent contentions",
        ],
        "recommended_drills": ["they_said_drill", "argument_map_exercise", "flow_listening"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 32, "proficient": 56, "mastery": 78,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["clash"],
    },

    "frontlining": {
        "id": "frontlining",
        "name": "Frontlining",
        "description": "Pre-preparing responses to predictable opponent attacks on your constructive arguments.",
        "novice_explanation": "Frontlines are responses you've prepared in advance for attacks you know are coming. If you run a tariff case, you know opponents will say 'trade wars retaliate.' Your frontline is the pre-written answer: 'Retaliation is overstated because...'",
        "prerequisites": ["warranting", "responses"],
        "speech_roles": ["rebuttal", "summary"],
        "success_criteria": [
            "Has at least 2 prepared frontlines per major contention",
            "Frontlines directly address the most common attack, not a straw man",
            "Frontlines include a warrant — not just 'they're wrong'",
        ],
        "recommended_drills": ["anticipation_drill", "frontline_writing", "attack_prediction"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "extensions": {
        "id": "extensions",
        "name": "Extensions",
        "description": "Carrying your constructive arguments forward through the round with added depth and adaptation.",
        "novice_explanation": "An extension means taking an argument from your constructive and making it stronger in summary or final focus. It's not re-reading the same evidence — it's re-establishing the claim, re-explaining why it's true, and answering any attacks against it.",
        "prerequisites": ["warranting"],
        "speech_roles": ["summary", "final_focus"],
        "success_criteria": [
            "Explicitly states the argument is being extended",
            "Restates the claim and warrant — doesn't just reference the evidence tag",
            "Responds to opponent attacks on the extended argument",
        ],
        "recommended_drills": ["extension_drill", "summary_focus_exercise", "claim_restatement"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["extensions"],
    },

    "responses": {
        "id": "responses",
        "name": "Responses (Drop Prevention)",
        "description": "Identifying and answering opponent arguments to prevent them from going uncontested.",
        "novice_explanation": "A 'drop' is when you fail to respond to an argument. In PF, drops matter — judges can vote on uncontested arguments. Drop prevention means tracking every opponent argument and giving at least a brief response to the most dangerous ones.",
        "prerequisites": ["clash"],
        "speech_roles": ["rebuttal", "summary"],
        "success_criteria": [
            "No opponent argument left completely unaddressed in rebuttal",
            "Top 2 opponent arguments get substantive responses (not just 'we disagree')",
            "Summary explicitly says which opponent arguments have been answered",
        ],
        "recommended_drills": ["flow_tracking", "response_bank_building", "priority_triage_drill"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["drops", "drop_prevention"],
    },

    "collapse": {
        "id": "collapse",
        "name": "Collapse",
        "description": "Strategically narrowing to 1-2 winning arguments in final focus.",
        "novice_explanation": "You can't win on every argument in final focus — you have 2 minutes. Collapse means choosing the arguments most likely to win the round, extending those with full depth, and letting the rest go. Judges reward strategic collapse over scattered coverage.",
        "prerequisites": ["weighing", "extensions"],
        "speech_roles": ["final_focus"],
        "success_criteria": [
            "Final focus covers no more than 2 voting issues",
            "The collapsed arguments are chosen because they're winnable, not just important",
            "Speech ends with a clear judge instruction: 'vote neg because...'",
        ],
        "recommended_drills": ["voting_issue_identification", "2_minute_collapse", "judge_instruction_drill"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "weighing": {
        "id": "weighing",
        "name": "Weighing",
        "description": "Arguing why your impacts matter more than the opponent's impacts.",
        "novice_explanation": "When both teams have good arguments, the judge needs a reason to prefer your side. Weighing means comparing your impact to theirs: 'Even if they win their economic argument, our lives argument outweighs because it is broader in scope and more certain to occur.'",
        "prerequisites": ["impact_explanation", "comparative_analysis"],
        "speech_roles": ["summary", "final_focus"],
        "success_criteria": [
            "At least one explicit weighing comparison in summary and final focus",
            "Weighing uses a standard: magnitude, probability, timeframe, or reversibility",
            "Weighing names the specific impact being compared — not generic 'ours is better'",
        ],
        "recommended_drills": ["weighing_standards_drill", "impact_comparison", "magnitude_vs_probability"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 32, "proficient": 56, "mastery": 78,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["weighing"],
    },

    "comparative_analysis": {
        "id": "comparative_analysis",
        "name": "Comparative Analysis",
        "description": "Directly comparing your arguments to the opponent's on the same dimensions.",
        "novice_explanation": "Comparative analysis means you put both teams' arguments side by side and explain why yours is better. It's not just 'we win' — it's 'our mechanism is faster, their evidence is outdated, our impact is more severe.'",
        "prerequisites": ["impact_explanation"],
        "speech_roles": ["summary", "final_focus"],
        "success_criteria": [
            "Explicitly compares your argument to a specific opponent argument",
            "Comparison uses a consistent dimension (not mixing magnitude vs. speed)",
            "Comparison is based on evidence quality or warrant strength — not just assertion",
        ],
        "recommended_drills": ["head_to_head_comparison", "apples_to_apples_drill", "dimension_practice"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "judge_adaptation": {
        "id": "judge_adaptation",
        "name": "Judge Adaptation",
        "description": "Adjusting your arguments and style based on the specific judge's preferences and background.",
        "novice_explanation": "Every judge is different. A tech worker parent who has never judged before needs crystal-clear explanations and human stakes. A former debater wants efficient argument coverage. Judge adaptation means reading the room and making strategic choices accordingly.",
        "prerequisites": ["audience_adaptation"],
        "speech_roles": ["constructive", "rebuttal", "summary", "final_focus"],
        "success_criteria": [
            "Pre-round paradigm check or judge research completed",
            "Speech style (speed, jargon level) matches judge type",
            "Voting issues are framed in the language the judge finds persuasive",
        ],
        "recommended_drills": ["judge_profile_study", "style_switching_drill", "paradigm_analysis"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "pf_argumentation",
        "legacy_aliases": ["judge_adaptation"],
    },

    "crossfire_questioning": {
        "id": "crossfire_questioning",
        "name": "Crossfire Questioning",
        "description": "Asking targeted questions that expose weaknesses in the opponent's case.",
        "novice_explanation": "Good crossfire questions are short and strategic. They don't let the opponent give a speech — they expose inconsistencies, missing warrants, or concessions. Best strategy: ask questions you already know the answer to.",
        "prerequisites": ["clash"],
        "speech_roles": ["crossfire"],
        "success_criteria": [
            "Questions are closed-ended or force a choice",
            "Follow-up question builds on the answer — doesn't abandon the line",
            "Extracts at least one concession or admission per crossfire",
        ],
        "recommended_drills": ["socratic_questioning", "yes_no_drill", "concession_hunting"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    "crossfire_answering": {
        "id": "crossfire_answering",
        "name": "Crossfire Answering",
        "description": "Answering opponent crossfire questions without making damaging concessions.",
        "novice_explanation": "Answering crossfire means giving short, confident answers that don't give away your case. Avoid long explanations — they let the opponent control the time. If you don't know, say 'I'll get to that in the speech.' Never concede a core argument.",
        "prerequisites": ["responses"],
        "speech_roles": ["crossfire"],
        "success_criteria": [
            "Answers are one or two sentences — not a full speech",
            "Does not concede a major argument without a prepared retort",
            "Can redirect a trap question without appearing evasive",
        ],
        "recommended_drills": ["hot_seat_drill", "concession_defense", "redirect_practice"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "pf_argumentation",
        "legacy_aliases": [],
    },

    # ── Speech Role (5) ────────────────────────────────────────────────────────

    "constructive_skill": {
        "id": "constructive_skill",
        "name": "Constructive Speech",
        "description": "Delivering the opening 4-minute prepared case with clarity, structure, and argument depth.",
        "novice_explanation": "The constructive is your team's prepared case. It should be fully scripted, hit time exactly, cover 2 contentions with claim-warrant-impact-evidence structure, and be delivered confidently.",
        "prerequisites": [],
        "speech_roles": ["constructive"],
        "success_criteria": [
            "Hits 3:45-4:00 of the allotted time",
            "Two distinct contentions each with claim, warrant, and impact",
            "At least one piece of cited evidence per contention",
            "Clear roadmap at the opening",
        ],
        "recommended_drills": ["timed_constructive", "contention_depth_drill", "case_audit"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "speech_role",
        "legacy_aliases": [],
    },

    "rebuttal_skill": {
        "id": "rebuttal_skill",
        "name": "Rebuttal Speech",
        "description": "Responding to the opponent's constructive while defending your own case in 4 minutes.",
        "novice_explanation": "The rebuttal is mostly impromptu — you respond to what they actually said, not what you predicted. Good rebuttalists flow everything, respond to the top 2 opponent contentions, and then quickly re-establish their own case.",
        "prerequisites": [],
        "speech_roles": ["rebuttal"],
        "success_criteria": [
            "Addresses at least 2 opponent contentions with substantive responses",
            "Defends own constructive from attacks",
            "Uses organized structure (e.g., 'on their first argument... on their second...')",
        ],
        "recommended_drills": ["impromptu_rebuttal", "flow_practice", "attack_and_defend"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "speech_role",
        "legacy_aliases": [],
    },

    "summary_skill": {
        "id": "summary_skill",
        "name": "Summary Speech",
        "description": "Collapsing to the key voting issues and weighing them in 3 minutes.",
        "novice_explanation": "Summary is where you start to narrow the debate. You can't cover everything — pick the 2-3 most important arguments, extend them, and explain why they're more important than the opponent's best argument.",
        "prerequisites": [],
        "speech_roles": ["summary"],
        "success_criteria": [
            "Covers no more than 3 voting issues",
            "Each extended argument restates claim and warrant, not just evidence tag",
            "Includes at least one weighing comparison",
        ],
        "recommended_drills": ["summary_structure_drill", "3_issue_collapse", "summary_timed"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "speech_role",
        "legacy_aliases": [],
    },

    "final_focus_skill": {
        "id": "final_focus_skill",
        "name": "Final Focus Speech",
        "description": "Delivering a 2-minute closing that gives the judge a clear reason to vote for you.",
        "novice_explanation": "Final focus is your last 2 minutes. Make it count. Collapse to 1-2 arguments, weigh them clearly, and end with a direct judge instruction. No new arguments — everything should be crystallization of what's already been said.",
        "prerequisites": [],
        "speech_roles": ["final_focus"],
        "success_criteria": [
            "Covers no more than 2 voting issues",
            "Ends with explicit judge instruction ('vote aff because...')",
            "Responds to or concedes the opponent's best final focus argument",
        ],
        "recommended_drills": ["2_min_final_focus", "judge_instruction_drill", "single_issue_collapse"],
        "mastery_thresholds": {
            "introducing": 12, "developing": 30, "proficient": 54, "mastery": 77,
        },
        "category": "speech_role",
        "legacy_aliases": [],
    },

    "crossfire_skill": {
        "id": "crossfire_skill",
        "name": "Crossfire",
        "description": "Engaging productively in the 3-minute question-and-answer period between speeches.",
        "novice_explanation": "Crossfire is a conversation, not a speech. Good crossfire debaters ask sharp questions, give short answers, stay calm under pressure, and use the time strategically — not just as a filler.",
        "prerequisites": [],
        "speech_roles": ["crossfire"],
        "success_criteria": [
            "Questions are 10 words or fewer",
            "Answers are 1-2 sentences",
            "Extracts or defends against at least one concession",
        ],
        "recommended_drills": ["question_quality_drill", "answer_brevity_drill", "grand_cx_simulation"],
        "mastery_thresholds": {
            "introducing": 10, "developing": 28, "proficient": 52, "mastery": 76,
        },
        "category": "speech_role",
        "legacy_aliases": [],
    },
}


# ── Legacy Skill Map ───────────────────────────────────────────────────────────
# Maps old (mission_recommender.py) skill names → canonical IDs.

LEGACY_SKILL_MAP: dict[str, str] = {
    "warranting":       "warranting",
    "weighing":         "weighing",
    "extensions":       "extensions",
    "drops":            "responses",
    "drop_prevention":  "responses",
    "evidence_use":     "evidence_use",
    "clash":            "clash",
    "judge_adaptation": "judge_adaptation",
    "delivery":         "clarity",   # primary mapping for legacy delivery skill
    "organization":     "organization",
}

# ── Canonical → Legacy (reverse map for the 9 legacy skills) ──────────────────
CANONICAL_TO_LEGACY: dict[str, str] = {
    "warranting":       "warranting",
    "weighing":         "weighing",
    "extensions":       "extensions",
    "responses":        "drops",
    "evidence_use":     "evidence_use",
    "clash":            "clash",
    "judge_adaptation": "judge_adaptation",
    "clarity":          "delivery",
    "organization":     "organization",
}

# ── Prerequisite Graph ────────────────────────────────────────────────────────

SKILL_PREREQUISITES: dict[str, list[str]] = {
    "warranting":           ["claim_construction"],
    "impact_explanation":   ["warranting"],
    "weighing":             ["impact_explanation", "comparative_analysis"],
    "comparative_analysis": ["impact_explanation"],
    "collapse":             ["weighing", "extensions"],
    "extensions":           ["warranting"],
    "frontlining":          ["warranting", "responses"],
    "responses":            ["clash"],
    "evidence_use":         ["citation_quality"],
    "judge_adaptation":     ["audience_adaptation"],
    "crossfire_questioning":["clash"],
    "crossfire_answering":  ["responses"],
    # No prerequisites:
    "claim_construction":   [],
    "clash":                [],
    "clarity":              [],
    "organization":         [],
    "pacing":               [],
    "emphasis":             [],
    "confidence":           [],
    "concision":            [],
    "audience_adaptation":  [],
    "evidence_explanation": [],
    "citation_quality":     [],
    "constructive_skill":   [],
    "rebuttal_skill":       [],
    "summary_skill":        [],
    "final_focus_skill":    [],
    "crossfire_skill":      [],
}


# ── Novice PF Curriculum (11 lessons) ─────────────────────────────────────────

NOVICE_PF_CURRICULUM: list[dict] = [
    {
        "id": "pf_novice_01",
        "title": "Case Structure: Building Your Constructive",
        "skill_id": "organization",
        "difficulty": "beginner",
        "prerequisite_lesson_ids": [],
        "estimated_minutes": 20,
        "what_is_it": (
            "A PF constructive is a 4-minute prepared speech with a roadmap, "
            "two contentions (each with a claim, warrant, and impact), and cited evidence. "
            "Structure is the skeleton that holds your arguments together."
        ),
        "why_judges_care": (
            "Judges flow your speech — they write notes while you talk. "
            "If your arguments aren't clearly labeled and separated, judges can't credit you for them. "
            "Clear structure turns speaking time into scored points."
        ),
        "weak_example": (
            "\"Today my partner and I will be talking about trade policy and how it affects people. "
            "First, tariffs raise prices. Also, jobs are important. We have evidence that says "
            "the economy goes down. In conclusion, vote for us.\""
        ),
        "strong_example": (
            "\"My partner and I negate the resolution. We'll run two contentions: "
            "one, tariffs increase consumer prices; two, tariffs reduce export competitiveness. "
            "Contention one — tariffs increase consumer prices. Claim: import tariffs directly raise "
            "the cost of goods for American families. Warrant: tariffs function as a tax on importers, "
            "who pass costs downstream to consumers. Evidence: Smith and Jones 2023 from the Peterson "
            "Institute found average household costs rose $1,400 per year under 25% tariffs. "
            "Impact: 18 million lower-income families face impossible budget trade-offs.\""
        ),
        "what_changed": (
            "The strong version has a roadmap, labeled contentions, and clear claim-warrant-evidence-impact "
            "structure within each contention. The judge knows exactly where they are in the speech."
        ),
        "recognition_check": (
            "After giving your speech, can a teammate who was only half-listening name both of "
            "your contentions and say what each one was about?"
        ),
        "micro_drill": (
            "Write a 60-second speech with exactly one contention. It must have: "
            "a labeled claim, a 'because' warrant, one cited piece of evidence, and one human impact. "
            "Read it aloud and time yourself."
        ),
        "speech_application": (
            "Before your next constructive, write a one-sentence roadmap and a one-sentence "
            "contention label for each argument. Practice saying them until they feel natural."
        ),
        "success_checklist": [
            "My speech opens with a roadmap that names both contentions",
            "Each contention is clearly labeled (e.g., 'Contention one: ...')",
            "Each contention has claim, warrant, evidence, and impact in that order",
            "I use a transition phrase to move between contentions",
            "My speech hits between 3:45 and 4:00",
        ],
        "common_mistakes": [
            "Skipping the roadmap and jumping directly into the first argument",
            "Reading contentions without signposting ('my first contention is...')",
            "Running over time by trying to include too many sub-points",
        ],
        "coach_note": (
            "Watch for students who list observations without organizing them under named contentions. "
            "Ask them to write out their roadmap sentence before recording."
        ),
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_02",
        "version": "1.0",
    },
    {
        "id": "pf_novice_02",
        "title": "Warranting: Why Your Claim Is True",
        "skill_id": "warranting",
        "difficulty": "beginner",
        "prerequisite_lesson_ids": ["pf_novice_01"],
        "estimated_minutes": 20,
        "what_is_it": (
            "A warrant is the logical mechanism that explains why your claim is true. "
            "Claims without warrants are just assertions — the judge has no reason to accept them. "
            "A warrant answers the question 'why?' after every claim you make."
        ),
        "why_judges_care": (
            "Experienced judges actively look for warrants. When a debater says 'tariffs hurt trade' "
            "without explanation, a good judge writes 'no warrant' on their flow and discounts the argument. "
            "Warrants are the difference between an argument and a statement."
        ),
        "weak_example": (
            "\"Tariffs harm the US economy. Studies show GDP declines when tariffs are imposed. "
            "Therefore, tariffs are bad policy.\""
        ),
        "strong_example": (
            "\"Tariffs harm the US economy because they function as a production tax. "
            "When the US government imposes a 25% tariff on steel imports, domestic manufacturers who "
            "rely on steel — like auto plants, construction firms, and appliance makers — face higher "
            "input costs. Those costs are passed to consumers or absorbed as reduced profit, both of "
            "which contract economic activity. Smith 2023 from the Economic Policy Institute confirms "
            "this mechanism: every 10% tariff on intermediate goods reduces downstream manufacturing "
            "output by 1.8%.\""
        ),
        "what_changed": (
            "The strong version explains the mechanism: tariffs → higher input costs → passed to "
            "consumers or profit reduction → economic contraction. The evidence confirms the mechanism, "
            "not just the conclusion."
        ),
        "recognition_check": (
            "Can you complete this sentence about your main argument: 'This is true because "
            "[specific causal mechanism]'? If you can only say 'this is true because studies show it,' "
            "you don't have a warrant yet."
        ),
        "micro_drill": (
            "Take one of your constructive claims. Write it at the top of a page. "
            "Below it, complete this sentence five times: 'This is true because...'. "
            "Pick the most specific, mechanistic explanation. That's your warrant."
        ),
        "speech_application": (
            "After stating each claim in your constructive, say 'because' out loud and complete "
            "the sentence with your warrant before moving to evidence."
        ),
        "success_checklist": [
            "Every claim in my speech is followed by a 'because' explanation",
            "My warrant describes a specific process or mechanism — not just 'studies show'",
            "My warrant is different from my claim (not circular)",
            "My evidence confirms the warrant mechanism, not just the conclusion",
        ],
        "common_mistakes": [
            "Restating the claim instead of explaining the mechanism",
            "Using 'because studies show' as a warrant (that is evidence, not mechanism)",
            "Jumping to impact before establishing the causal link",
        ],
        "coach_note": "Have students fill in: 'X causes Y because [mechanism], which leads to Z.' If they cannot complete it, they lack a warrant.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_03",
        "version": "1.0",
    },
    {
        "id": "pf_novice_03",
        "title": "Evidence Use: Cards That Actually Prove Things",
        "skill_id": "evidence_use",
        "difficulty": "beginner",
        "prerequisite_lesson_ids": ["pf_novice_02"],
        "estimated_minutes": 20,
        "what_is_it": (
            "Evidence use is the practice of selecting, citing, and explaining evidence so it "
            "directly proves your specific claim. Good evidence use requires citing the author and "
            "year, reading a relevant passage, and explaining how it connects to your argument."
        ),
        "why_judges_care": (
            "Evidence is supposed to be external verification that your claim is true. "
            "If you misuse evidence — reading a vague passage, skipping the citation, or using "
            "a card that doesn't match your claim — the judge may strike the evidence entirely "
            "or weigh it very little."
        ),
        "weak_example": (
            "\"A study found that trade policy has many complex effects on the economy. "
            "This proves that tariffs are harmful.\""
        ),
        "strong_example": (
            "\"Smith and Jones writing for the Peterson Institute in 2023 found — and I quote — "
            "'a 25% tariff on imported steel increased domestic auto production costs by an "
            "average of $1,200 per vehicle.' This directly proves our claim: tariffs raise "
            "production costs for American manufacturers who rely on imported inputs.\""
        ),
        "what_changed": (
            "The strong version names the author, institution, and year; quotes a specific finding "
            "with numbers; and explicitly connects the evidence back to the claim."
        ),
        "recognition_check": (
            "For your next speech, pause after each card and ask: does this evidence actually "
            "say what I claim it says? Or am I inferring more than the source provides?"
        ),
        "micro_drill": (
            "Find two pieces of evidence you use in your constructive. For each one, write: "
            "(1) the exact citation (author, year, publication), (2) the specific sentence or "
            "statistic that proves your claim, and (3) one sentence explaining the link."
        ),
        "speech_application": (
            "Practice the three-step evidence sequence: 'According to [Author, Year from Publication]... "
            "[quote or paraphrase the specific finding]... This proves [restate your claim].'"
        ),
        "success_checklist": [
            "Every card is cited with author last name and year at minimum",
            "The specific passage I read actually contains the claim I'm making",
            "After the card, I say 'this proves' or 'this shows' and restate the claim",
            "I can name the source's institution or publication to establish credibility",
        ],
        "common_mistakes": [
            "Citing without reading the key sentence aloud",
            "Using evidence that is too long — paraphrase, then quote only the key line",
            "Forgetting author last name and year in the citation",
        ],
        "coach_note": "Require tag-cite-read format in every practice speech. If any step is missing, stop and have them redo the card.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_04",
        "version": "1.0",
    },
    {
        "id": "pf_novice_04",
        "title": "Clash and Responses: Engaging What They Actually Said",
        "skill_id": "clash",
        "difficulty": "beginner",
        "prerequisite_lesson_ids": ["pf_novice_03"],
        "estimated_minutes": 25,
        "what_is_it": (
            "Clash means directly engaging the opponent's arguments. A response is your answer "
            "to a specific opponent argument. Without clash, two teams can give great speeches "
            "that talk past each other — and the judge has no debate to evaluate."
        ),
        "why_judges_care": (
            "Judges vote based on who won the argument, not who gave the better speech in isolation. "
            "If you ignore the opponent's strongest argument, the judge may treat it as uncontested "
            "and vote against you — even if your own arguments were excellent."
        ),
        "weak_example": (
            "\"My opponents said things about the economy, but we disagree. "
            "Our evidence says tariffs are bad. Now back to our contentions.\""
        ),
        "strong_example": (
            "\"On my opponent's first contention — the job creation argument. "
            "They claim tariffs protect manufacturing jobs by shielding domestic industries. "
            "That's false because the protected jobs come at the cost of jobs in downstream industries: "
            "for every job saved in steel manufacturing, 16 jobs are lost in steel-consuming industries "
            "like auto and construction — that's Francois and Baughman 2018 from ECIPE. "
            "Our evidence directly refutes their mechanism.\""
        ),
        "what_changed": (
            "The strong version names the argument, states what the opponent claimed, explains "
            "why it's wrong with a specific counter-mechanism, and cites evidence for the refutation."
        ),
        "recognition_check": (
            "After flowing your opponent's constructive, can you name their two main contentions "
            "and write a one-sentence response to each? If not, you need more flow practice."
        ),
        "micro_drill": (
            "Listen to a 2-minute speech (from a partner or recording). "
            "Write their arguments on a flow sheet. Then give a 90-second response covering "
            "their top argument with: name the argument, give your response, cite evidence if you have it."
        ),
        "speech_application": (
            "In your next rebuttal, open with: 'On their first argument, [name it]. "
            "They claim [their claim]. That's wrong because [your warrant].'"
        ),
        "success_checklist": [
            "I name the opponent's argument before responding to it",
            "My response addresses their mechanism — not just their conclusion",
            "I cover their top 2 arguments before returning to my own case",
            "My response includes a reason (warrant) not just 'we disagree'",
        ],
        "common_mistakes": [
            "Ignoring opponent arguments entirely (silent drops)",
            "Saying 'I disagree' without explaining why",
            "Responding to one sub-point but dropping the impact",
        ],
        "coach_note": "Give students an opponent speech transcript and have them write 'they say... but...' responses before recording.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_05",
        "version": "1.0",
    },
    {
        "id": "pf_novice_05",
        "title": "Frontlining: Pre-Preparing Your Defenses",
        "skill_id": "frontlining",
        "difficulty": "intermediate",
        "prerequisite_lesson_ids": ["pf_novice_04"],
        "estimated_minutes": 25,
        "what_is_it": (
            "Frontlines are prepared responses to predictable attacks on your constructive arguments. "
            "Since opponents often run similar attacks across rounds, you can pre-write answers "
            "and have them ready before the tournament."
        ),
        "why_judges_care": (
            "Frontlines make rebuttals faster, stronger, and more responsive. "
            "A debater who can instantly defend their constructive sounds prepared and confident. "
            "A debater who seems surprised by predictable attacks looks underprepared."
        ),
        "weak_example": (
            "\"Um, yes, they raised that argument about trade wars. We think that's not very "
            "likely to happen based on... I think there's some evidence that says... "
            "I'll have to look it up.\""
        ),
        "strong_example": (
            "\"On the trade war retaliation argument — that's our first frontline. "
            "Retaliation is overstated for three reasons: first, US trading partners threatened "
            "retaliation but historically settled rather than escalate; second, US market size "
            "gives us leverage — trading partners need US consumers more than vice versa; "
            "third, Bown 2022 at PIIE shows only 12% of threatened retaliatory tariffs were "
            "actually implemented.\""
        ),
        "what_changed": (
            "The strong version has a pre-prepared numbered response with three specific sub-points "
            "and evidence. It sounds rehearsed because it was — that's a good thing."
        ),
        "recognition_check": (
            "List the three most common attacks on your constructive's main contention. "
            "Do you have a prepared answer (claim + warrant) for each one?"
        ),
        "micro_drill": (
            "For your strongest contention, write 3 'attacks' an opponent might make. "
            "For each attack, write a 3-sentence frontline: (1) acknowledge the attack, "
            "(2) give your counter-warrant, (3) cite evidence or logic."
        ),
        "speech_application": (
            "Before your next tournament, write and practice 2 frontlines for each of your contentions. "
            "Practice until you can deliver each frontline in under 30 seconds."
        ),
        "success_checklist": [
            "I have at least 2 frontlines written for each main contention",
            "Each frontline names the attack, gives a counter-reason, and cites support",
            "Frontlines are practiced enough that I can deliver them under time pressure",
            "My frontlines address the mechanism of the attack — not just the conclusion",
        ],
        "common_mistakes": [
            "Just repeating the original argument rather than rebuilding after a response",
            "Frontlining with 'my evidence is better' without explaining why",
            "Missing the 'even if they are right' concession-and-extend move",
        ],
        "coach_note": "Teach: 'Their response says X. But even if X, our argument still stands because Y. Moreover, our evidence from Z confirms...'",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_06",
        "version": "1.0",
    },
    {
        "id": "pf_novice_06",
        "title": "Summary Extensions: Keeping Your Arguments Alive",
        "skill_id": "extensions",
        "difficulty": "intermediate",
        "prerequisite_lesson_ids": ["pf_novice_05"],
        "estimated_minutes": 25,
        "what_is_it": (
            "An extension is what you do in summary and final focus to keep a constructive argument "
            "alive in the round. It means restating the claim, warrant, and why it still stands "
            "despite any opponent responses. You can't just reference 'our second contention' — "
            "you have to rebuild it briefly."
        ),
        "why_judges_care": (
            "Judges only vote on arguments that have been properly extended — especially in summary. "
            "If you don't explicitly extend an argument, it may be treated as dropped, even if you "
            "said it in the constructive. Summary is where extensions get locked in."
        ),
        "weak_example": (
            "\"We're extending our second contention about jobs. The evidence is still good. "
            "They didn't really answer it well. Please extend.\""
        ),
        "strong_example": (
            "\"Extending our second contention — tariff-driven job losses in downstream industries. "
            "Claim: for every job protected in steel, 16 are lost downstream. Warrant: this is "
            "because steel-consuming sectors like auto and construction face higher input costs "
            "and must cut labor. The opponents said this evidence is outdated — our Baughman 2021 "
            "update is post-COVID and confirms the ratio held even with supply chain disruptions. "
            "The extension stands.\""
        ),
        "what_changed": (
            "The strong version re-states the claim and warrant explicitly, answers the attack "
            "on the evidence, and declares the extension clearly. The judge can write it on their flow."
        ),
        "recognition_check": (
            "After your summary speech, can a teammate who hasn't heard your constructive tell you "
            "exactly what your extended argument says — including the mechanism — just from your summary?"
        ),
        "micro_drill": (
            "Pick one constructive argument. Write a 30-second extension script that includes: "
            "(1) 'Extending [name]', (2) the claim restated in one sentence, "
            "(3) the warrant in one sentence, (4) the response to the top attack."
        ),
        "speech_application": (
            "In your next summary, use the phrase 'extending our [contention name]' to signal each extension. "
            "Then restate claim, restate warrant, answer the biggest attack in one sentence."
        ),
        "success_checklist": [
            "I use the word 'extending' to signal each extension explicitly",
            "I restate the claim in one sentence — not just the contention title",
            "I restate the warrant — not just reference the evidence tag",
            "I answer the opponent's top response to this argument before declaring it extended",
        ],
        "common_mistakes": [
            "Extending only the claim, not the warrant and impact",
            "Failing to note that the opponent never responded to the argument",
            "Reading the card again without explaining why it still matters",
        ],
        "coach_note": "Require the phrase 'they never answered' followed by the warrant restatement in every extension drill.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_07",
        "version": "1.0",
    },
    {
        "id": "pf_novice_07",
        "title": "Impact Explanation: Why Judges Should Care",
        "skill_id": "impact_explanation",
        "difficulty": "intermediate",
        "prerequisite_lesson_ids": ["pf_novice_06"],
        "estimated_minutes": 20,
        "what_is_it": (
            "An impact is the real-world consequence of your argument. It's not enough to say "
            "'the economy shrinks' — you need to explain what that means for actual people. "
            "Impacts answer: how bad is it, who does it affect, and why should the judge care?"
        ),
        "why_judges_care": (
            "Judges need a reason to feel the stakes of the debate. An underdeveloped impact "
            "leaves the judge with no emotional or logical anchor. Vivid, specific impacts "
            "help the judge understand what's on the line and are more persuasive."
        ),
        "weak_example": (
            "\"This is bad for the economy. There are major consequences. "
            "It affects many people. Therefore you should vote for us.\""
        ),
        "strong_example": (
            "\"The impact is job displacement for 2 million workers in steel-consuming industries. "
            "These are auto assembly workers in Ohio, construction workers in Texas, appliance "
            "manufacturers in Wisconsin — people who can't easily retrain. When they lose their jobs, "
            "their families lose healthcare, their communities lose tax revenue, and local schools "
            "and services cut funding. That's not an abstract GDP number — that's a cascading "
            "collapse of working-class stability across the Rust Belt.\""
        ),
        "what_changed": (
            "The strong version names specific populations, specific states, specific secondary "
            "effects, and paints a concrete picture of the harm. The judge can visualize the stakes."
        ),
        "recognition_check": (
            "For your top contention, can you answer: who specifically is harmed, how many, "
            "what specifically happens to them, and why can't they just recover?"
        ),
        "micro_drill": (
            "Take your main impact ('GDP falls' or 'jobs are lost'). "
            "Write the next three things that happen as a result. Then write three more. "
            "Keep going until you reach a human harm that a judge can picture."
        ),
        "speech_application": (
            "Add one sentence to each impact in your constructive that names a specific population "
            "and the specific harm they experience."
        ),
        "success_checklist": [
            "My impact names at least one specific population affected",
            "My impact gives a sense of scale (how many, how severe)",
            "My impact explains a concrete harm — not just an economic metric",
            "My impact is connected causally to my warrant — not just added on",
        ],
        "common_mistakes": [
            "Listing multiple impacts without explaining which is biggest",
            "Using vague impact language such as 'it will be really bad'",
            "Failing to quantify or time the impact",
        ],
        "coach_note": "Have students answer: How big? How likely? How fast? Reversible? Those four questions produce a complete impact.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_08",
        "version": "1.0",
    },
    {
        "id": "pf_novice_08",
        "title": "Weighing: Winning the Impact Comparison",
        "skill_id": "weighing",
        "difficulty": "intermediate",
        "prerequisite_lesson_ids": ["pf_novice_07"],
        "estimated_minutes": 25,
        "what_is_it": (
            "Weighing is the practice of comparing your impacts to the opponent's impacts and "
            "arguing why yours matter more. Even if both teams win arguments, the judge still "
            "needs to decide — weighing gives them the framework."
        ),
        "why_judges_care": (
            "In close rounds, the judge often says: 'both teams made good arguments — I voted "
            "neg because they weighed better.' Weighing is the most directly persuasive thing "
            "you can do in summary and final focus."
        ),
        "weak_example": (
            "\"Our impacts are bigger than theirs. Our argument is more important. "
            "Therefore, vote for us.\""
        ),
        "strong_example": (
            "\"Even if they win that tariffs create some steel jobs — weigh our impact against "
            "theirs by magnitude: their benefit is 25,000 steel jobs at risk. Our harm is 400,000 "
            "downstream manufacturing jobs lost plus 18 million families facing $1,400/year higher "
            "costs. On magnitude alone, our impact is 16 times larger. And on probability — their "
            "job creation depends on domestic steel demand holding, which Bown 2022 shows is "
            "increasingly uncertain as US manufacturers substitute materials. Our harm is certain "
            "because input cost increases are automatic and contractual.\""
        ),
        "what_changed": (
            "The strong version picks a specific weighing standard (magnitude), names exact numbers "
            "from both sides, compares them directly, then adds a second standard (probability) "
            "to show the comparison holds on multiple dimensions."
        ),
        "recognition_check": (
            "What is the opponent's best impact? What is your best impact? "
            "On which standard (magnitude, probability, timeframe, reversibility) does yours clearly win?"
        ),
        "micro_drill": (
            "Write a 45-second weighing block comparing your top impact to a hypothetical "
            "opponent impact. Use this template: 'Even if they win [X], weigh by [standard]: "
            "our impact is [comparison]. On probability, [explanation].'"
        ),
        "speech_application": (
            "In summary, after your last extension, add: 'Even if they win their [argument], "
            "weigh by [magnitude/probability/timeframe] — our impact is [specifically] larger because...'"
        ),
        "success_checklist": [
            "I name the specific opponent impact I'm comparing against",
            "I use at least one named weighing standard (magnitude, probability, timeframe, reversibility)",
            "I give concrete numbers or specific evidence for the comparison",
            "The weighing block is in both summary and final focus",
        ],
        "common_mistakes": [
            "Asserting 'our impacts outweigh' without using a weighing mechanism",
            "Comparing incomparable things without a linking standard",
            "Doing weighing only in Final Focus instead of building it throughout",
        ],
        "coach_note": "Require students to name the mechanism: magnitude, timeframe, probability, or reversibility. 'Our impact is bigger' is not enough.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_09",
        "version": "1.0",
    },
    {
        "id": "pf_novice_09",
        "title": "Final Focus Collapse: Winning on Two Issues",
        "skill_id": "collapse",
        "difficulty": "intermediate",
        "prerequisite_lesson_ids": ["pf_novice_08"],
        "estimated_minutes": 20,
        "what_is_it": (
            "Collapse is the strategic decision to cover only 1-2 arguments in final focus "
            "instead of trying to cover everything. In two minutes, you can either cover four "
            "arguments shallowly or two arguments deeply. Deep wins rounds."
        ),
        "why_judges_care": (
            "Judges make their decision based on the most persuasive argument, not the longest list. "
            "A debater who collapses and explains one argument well is more persuasive than one "
            "who sprints through five arguments superficially."
        ),
        "weak_example": (
            "\"Okay so in final focus we have our jobs argument, and also the economy argument, "
            "and also the sovereignty argument, and also we answer their environment contention, "
            "and their second contention is also dropped, and our evidence is better, so vote for us.\""
        ),
        "strong_example": (
            "\"We collapse to one voting issue: the downstream job displacement argument. "
            "Here's why you vote on this: it's the only argument with evidence from post-2022 data, "
            "the opponents' entire job-creation case relies on 2018 projections that didn't materialize, "
            "and on magnitude, 400,000 jobs outweigh 25,000. The opponents' best argument in final focus "
            "was the sovereignty issue — concede it doesn't resolve the economic harm. "
            "Vote neg: the only evidence-backed impact in this round goes to our side.\""
        ),
        "what_changed": (
            "The strong version explicitly collapses, explains why this is the voting issue, "
            "answers the opponent's final focus argument, and ends with a direct judge instruction."
        ),
        "recognition_check": (
            "Before your final focus: which one or two arguments, if you win them, win the round? "
            "Can you give those arguments with full depth in under two minutes?"
        ),
        "micro_drill": (
            "Choose one argument from a flow sheet. Write a 90-second final focus script that "
            "covers only that argument with: claim restatement, warrant, evidence, impact weighing, "
            "and a judge instruction. Practice until it flows naturally."
        ),
        "speech_application": (
            "Open your final focus with: 'We collapse to [argument name]. "
            "Here's why this is the ballot: [explanation].' "
            "Cover nothing else until that argument is fully defended."
        ),
        "success_checklist": [
            "Final focus covers no more than 2 voting issues",
            "I explicitly say which argument I'm collapsing to",
            "Each collapsed argument has claim, warrant, and weighing",
            "I end with a direct judge instruction: 'Vote [aff/neg] because...'",
            "I at least acknowledge the opponent's best final focus argument",
        ],
        "common_mistakes": [
            "Trying to cover too many arguments instead of collapsing to the best two",
            "Repeating the same point rather than adding new depth",
            "Collapsing without connecting back to the voting issue",
        ],
        "coach_note": "Final Focus is about depth, not breadth. Require students to pick one argument and develop claim, warrant, impact, and weighing fully before adding anything else.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_10",
        "version": "1.0",
    },
    {
        "id": "pf_novice_10",
        "title": "Crossfire Fundamentals: Asking Questions That Matter",
        "skill_id": "crossfire_questioning",
        "difficulty": "intermediate",
        "prerequisite_lesson_ids": ["pf_novice_09"],
        "estimated_minutes": 20,
        "what_is_it": (
            "Crossfire is the 3-minute period where both teams ask and answer questions. "
            "Good crossfire questioning means asking short, targeted questions that expose "
            "weaknesses in the opponent's case — not giving speeches or asking vague open-ended questions."
        ),
        "why_judges_care": (
            "Crossfire concessions can be referenced in subsequent speeches. "
            "'As they conceded in crossfire, their evidence doesn't account for...' "
            "is a powerful speech moment. Good crossfire technique creates these moments."
        ),
        "weak_example": (
            "\"So, um, what do you think about the idea that your evidence might not fully "
            "account for all the complex economic factors that could potentially affect "
            "the outcomes you're describing?\""
        ),
        "strong_example": (
            "\"Your steel jobs claim — is that based on pre-tariff or post-tariff data? "
            "... Pre-tariff. So your evidence doesn't account for the retaliatory tariffs "
            "China imposed in 2018? ... I'm not sure. So you can't confirm your evidence "
            "accounts for the second-order effects we're describing. Thank you.\""
        ),
        "what_changed": (
            "The strong version asks closed questions, builds a logical chain, and extracts "
            "a specific admission ('I'm not sure') that can be referenced in a later speech."
        ),
        "recognition_check": (
            "After your last crossfire, what specific fact or admission did you extract "
            "that you could reference in your next speech? If nothing, you need better questions."
        ),
        "micro_drill": (
            "Look at an opponent argument from a practice flow. Write 5 questions you could ask "
            "about it. Each question must be answerable with 'yes', 'no', or a number. "
            "No open-ended 'what do you think' questions."
        ),
        "speech_application": (
            "In your next crossfire, start with: 'Quick question about your [specific contention] — "
            "[yes/no question]?' Build from the answer. Don't move to a new topic until you've "
            "extracted something useful from the first one."
        ),
        "success_checklist": [
            "My questions are 10 words or fewer",
            "My questions are answerable with yes, no, or a specific fact",
            "I follow up on the answer before moving to a new topic",
            "I extract at least one usable concession or uncertainty",
            "I reference a crossfire admission in my next speech",
        ],
        "common_mistakes": [
            "Asking unfocused questions that do not expose any gap",
            "Getting baited into answering questions they cannot win",
            "Forgetting that crossfire time is for the judge, not just the opponent",
        ],
        "coach_note": "Have students write 3 crossfire questions for every speech. Grade them: does the question expose a gap, set up a turn, or establish a concession?",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_11",
        "version": "1.0",
    },
    {
        "id": "pf_novice_11",
        "title": "Judge Adaptation: Reading the Room",
        "skill_id": "judge_adaptation",
        "difficulty": "advanced",
        "prerequisite_lesson_ids": ["pf_novice_10"],
        "estimated_minutes": 25,
        "what_is_it": (
            "Judge adaptation means adjusting your style, speed, vocabulary, and argument framing "
            "based on the specific judge you're in front of. Every judge is different — and the "
            "team that best adapts to the judge often wins close rounds."
        ),
        "why_judges_care": (
            "Judges vote based on who persuaded them, not who had the best technical arguments. "
            "A brilliant technical case delivered at 300 WPM to a parent judge loses. "
            "A clear, slow, story-driven case wins that same round."
        ),
        "weak_example": (
            "\"[Speaking to a lay parent judge at 250 WPM in dense policy jargon] "
            "The net benefit outweighs on a probability-magnitude-timeframe calculus because "
            "the counterfactual impact threshold is empirically denied by the literature...\""
        ),
        "strong_example": (
            "\"[Reading the judge — parent, no badge, watching patiently] "
            "[Slowing to 150 WPM, clear diction, leaning forward] "
            "'Here's what this debate comes down to: should the government charge extra fees "
            "on imported products? We say no — and here's why it hurts American families "
            "who are already struggling with high prices. Picture this: a family in Ohio "
            "who buys a new washing machine...' [human story, concrete, no jargon]\""
        ),
        "what_changed": (
            "The strong version reads the judge's background from visual cues, adjusts speed "
            "dramatically, eliminates jargon, and opens with a human story rather than theory."
        ),
        "recognition_check": (
            "Before your next round: check the judge's paradigm if available. "
            "If not, look at their age, dress, and engagement. "
            "What speed and vocabulary level will they respond to best?"
        ),
        "micro_drill": (
            "Take one of your constructive contentions and deliver it two ways: "
            "once for a flow judge (faster, more technical, jargon OK), "
            "once for a lay parent judge (slow, stories, plain language). "
            "Record both and compare."
        ),
        "speech_application": (
            "At the start of every round, make a mental note: 'This judge is [lay/flow/technical]. "
            "I will adjust my speed to [X WPM] and my framing to [story-driven/technical/impact-focused].' "
            "Then execute that plan."
        ),
        "success_checklist": [
            "I check the judge paradigm or make a read before the round starts",
            "My speech speed matches the judge's apparent experience level",
            "I eliminate or define jargon for lay judges",
            "My impacts are framed in the language the judge finds most persuasive",
            "I maintain eye contact with the judge to gauge comprehension",
        ],
        "common_mistakes": [
            "Using the same speech style regardless of whether the judge is lay or flow",
            "Over-adjusting and losing substance in an attempt to be accessible",
            "Failing to read judge non-verbal cues such as confusion or slow writing",
        ],
        "coach_note": "Role-play as different judge types. Give the same argument to a lay parent judge and then to a flow judge and compare what changes.",
        "author": "RoundLab Curriculum Team",
        "reviewed_date": "2026-06-27",
        "recommended_next": "pf_novice_01",
        "version": "1.0",
    },
]


# ── Novice Track ───────────────────────────────────────────────────────────────

NOVICE_TRACK: dict = {
    "id": "novice_pf",
    "name": "Novice Public Forum Fundamentals",
    "event_pack": "public_forum",
    "lesson_ids": [
        "pf_novice_01", "pf_novice_02", "pf_novice_03", "pf_novice_04",
        "pf_novice_05", "pf_novice_06", "pf_novice_07", "pf_novice_08",
        "pf_novice_09", "pf_novice_10", "pf_novice_11",
    ],
    "target_skills": [
        "organization", "warranting", "evidence_use", "clash", "frontlining",
        "extensions", "impact_explanation", "weighing", "collapse",
        "crossfire_questioning", "judge_adaptation",
    ],
    "description": (
        "An 11-lesson foundational curriculum for first-year and novice PF debaters. "
        "Covers the full constructive-rebuttal-summary-final-focus-crossfire arc with "
        "debate-native examples, micro drills, and speech application for each skill."
    ),
}


# ── Full Event Pack ────────────────────────────────────────────────────────────

EVENT_PACK: dict = {
    "id": "public_forum",
    "name": "Public Forum Debate",
    "speech_roles": [
        {"id": "constructive",  "label": "Constructive",  "minutes": 4},
        {"id": "rebuttal",      "label": "Rebuttal",      "minutes": 4},
        {"id": "summary",       "label": "Summary",       "minutes": 3},
        {"id": "final_focus",   "label": "Final Focus",   "minutes": 2},
        {"id": "crossfire",     "label": "Crossfire",     "minutes": 3},
    ],
    "skills": SKILL_REGISTRY,
    "curriculum": NOVICE_PF_CURRICULUM,
    "tracks": [NOVICE_TRACK],
    "rubric_dimensions": [
        {
            "id": "case_structure",
            "label": "Case Structure",
            "max_score": 20,
            "maps_to_skill": "organization",
            "description": "Clarity of roadmap, contention labeling, and structural flow.",
        },
        {
            "id": "warranting",
            "label": "Warranting",
            "max_score": 20,
            "maps_to_skill": "warranting",
            "description": "Mechanistic reasoning explaining why claims are true.",
        },
        {
            "id": "evidence_use",
            "label": "Evidence Use",
            "max_score": 20,
            "maps_to_skill": "evidence_use",
            "description": "Accuracy, citation quality, and strategic evidence deployment.",
        },
        {
            "id": "clash",
            "label": "Clash & Responses",
            "max_score": 20,
            "maps_to_skill": "clash",
            "description": "Direct engagement with opponent arguments.",
        },
        {
            "id": "weighing",
            "label": "Weighing",
            "max_score": 20,
            "maps_to_skill": "weighing",
            "description": "Impact comparison using explicit standards.",
        },
        {
            "id": "delivery",
            "label": "Delivery",
            "max_score": 20,
            "maps_to_skill": "clarity",
            "description": "Clarity, pacing, emphasis, and judge connection.",
        },
    ],
}


# ── Helper Functions ───────────────────────────────────────────────────────────

def get_skill(skill_id: str) -> dict | None:
    """Return skill dict by ID, or None if not found."""
    return SKILL_REGISTRY.get(skill_id)


def get_lesson(lesson_id: str) -> dict | None:
    """Return lesson dict by ID, or None if not found."""
    for lesson in NOVICE_PF_CURRICULUM:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def resolve_legacy_skill(legacy_name: str) -> str:
    """
    Map a legacy skill name to the canonical skill ID.
    Returns the input unchanged if no mapping is found.
    """
    return LEGACY_SKILL_MAP.get(legacy_name, legacy_name)


def get_prerequisites_met(skill_id: str, mastered_skills: set[str]) -> bool:
    """
    Return True if all prerequisites for skill_id are in mastered_skills.
    Skills with no prerequisites always return True.
    """
    prereqs = SKILL_PREREQUISITES.get(skill_id, [])
    return all(p in mastered_skills for p in prereqs)
