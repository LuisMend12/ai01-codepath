"""Combine the two signal scores into one calibrated confidence score.

Weights and thresholds were tuned empirically against the four test
passages in planning.md / README ("Confidence Scoring" section) — see
README "Spec Reflection" for how these diverged from the first draft in
planning.md.
"""

LLM_WEIGHT = 0.65
STYLOMETRIC_WEIGHT = 0.35

LIKELY_AI_THRESHOLD = 0.70
LIKELY_HUMAN_THRESHOLD = 0.40


def combine_scores(llm_score: float, stylometric_score: float) -> float:
    combined = LLM_WEIGHT * llm_score + STYLOMETRIC_WEIGHT * stylometric_score
    return round(max(0.0, min(1.0, combined)), 4)


def classify(combined_score: float) -> str:
    """Map a combined score to one of three attribution buckets.

    Thresholds are intentionally asymmetric: it takes more evidence to
    call something AI-generated (>= 0.70) than to call it human
    (<= 0.40), because a false "this is AI" accusation harms a real
    creator more than a missed AI detection does.
    """
    if combined_score >= LIKELY_AI_THRESHOLD:
        return "likely_ai"
    if combined_score <= LIKELY_HUMAN_THRESHOLD:
        return "likely_human"
    return "uncertain"
