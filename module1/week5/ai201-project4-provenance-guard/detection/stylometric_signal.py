"""Stylometric heuristics signal — pure Python, no external libraries.

Combines three structural sub-metrics into a single AI-probability score:
1. Sentence-length coefficient of variation (uniformity)
2. Type-token ratio (lexical diversity)
3. AI marker-phrase density

See planning.md, "Detection Signals -> Signal 2" for the rationale behind
each metric and the blend weights.
"""

import re
import statistics

AI_MARKER_PHRASES = [
    "it is important to note",
    "it's important to note",
    "in today's fast-paced world",
    "delve into",
    "navigate the complexities",
    "as an ai language model",
    "tapestry",
    "boasts",
    "underscores the importance",
    "plays a pivotal role",
    "in conclusion",
    "furthermore",
    "in the realm of",
    "testament to",
    "let's dive in",
    "unlock the potential",
]

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s+|$)")
_WORD_RE = re.compile(r"[A-Za-z']+")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def analyze_stylometry(text: str) -> dict:
    """Return stylometric sub-metrics plus a combined AI-probability score."""
    words = _WORD_RE.findall(text)
    total_words = len(words)

    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    sentence_lengths = [len(_WORD_RE.findall(s)) for s in sentences if _WORD_RE.findall(s)]

    # 1. Sentence-length uniformity (coefficient of variation).
    # Needs >= 2 sentences to be meaningful; otherwise stay neutral.
    if len(sentence_lengths) >= 2 and statistics.mean(sentence_lengths) > 0:
        mean_len = statistics.mean(sentence_lengths)
        cv = statistics.stdev(sentence_lengths) / mean_len
        uniformity_score = _clamp((0.6 - cv) / 0.6)
    else:
        cv = None
        uniformity_score = 0.5

    # 2. Type-token ratio (lexical diversity). Low TTR -> repetitive -> AI-ish.
    if total_words > 0:
        ttr = len({w.lower() for w in words}) / total_words
        low_ttr_score = _clamp((0.55 - ttr) / 0.55)
    else:
        ttr = None
        low_ttr_score = 0.5

    # 3. AI marker-phrase density per 100 words.
    lowered = text.lower()
    marker_hits = sum(lowered.count(phrase) for phrase in AI_MARKER_PHRASES)
    if total_words > 0:
        marker_density = marker_hits / (total_words / 100)
        marker_score = _clamp(marker_density / 2)
    else:
        marker_density = 0.0
        marker_score = 0.0

    stylometric_score = (
        0.45 * uniformity_score + 0.30 * marker_score + 0.25 * low_ttr_score
    )

    return {
        "stylometric_score": round(_clamp(stylometric_score), 4),
        "metrics": {
            "sentence_count": len(sentence_lengths),
            "sentence_length_cv": round(cv, 4) if cv is not None else None,
            "type_token_ratio": round(ttr, 4) if ttr is not None else None,
            "marker_phrase_hits": marker_hits,
            "marker_density_per_100_words": round(marker_density, 4),
        },
    }
