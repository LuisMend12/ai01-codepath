"""
Turn data/raw_posts.csv into data/labeled_dataset.csv.

Label taxonomy (see planning.md for full definitions):
  - ask_hn:  the OP is asking the community a question / soliciting opinions
  - show_hn: the OP is showing off something they made, inviting feedback
  - story:   the OP is sharing third-party content (a link) for discussion

Labels come from which Algolia HN tag the post was pulled under (ask_hn /
show_hn / story-not-ask-or-show) — a real distinction the HN submission
flow and community already enforce, not something we invented post hoc.

Because the "Ask HN:" / "Show HN:" title prefix is the single biggest
giveaway for those categories, we strip it from the title before building
the model-input `text` field. Otherwise a classifier (and the Groq
baseline) could "solve" the task by pattern-matching the literal prefix
string instead of learning anything about how the three kinds of posts are
actually written.

This script also flags a sample of structurally borderline posts (e.g. a
"story" post phrased as a direct question, or an "ask_hn" post that's
really just dropping a link) into flagged_for_review.csv for manual
inspection — see README.md's "difficult to label" section for what we
decided on a few of these.
"""
import csv
import html
import os
import random
import re

random.seed(42)

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw_posts.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "labeled_dataset.csv")
REVIEW_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "flagged_for_review.csv")

MAX_PER_LABEL = 90  # caps total dataset size so CPU fine-tuning stays fast
MIN_TEXT_LEN = 15

PREFIX_RE = re.compile(r"^\s*(ask|show|tell)\s*hn\s*:\s*", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")

QUESTION_HEUR_RE = re.compile(r"\?\s*$")
SHOW_HEUR_RE = re.compile(r"^(i (built|made|created|wrote)|i'm building)", re.IGNORECASE)


def clean_html(raw):
    if not raw:
        return ""
    text = html.unescape(raw)
    text = TAG_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def clean_title(title):
    title = PREFIX_RE.sub("", title)
    return WHITESPACE_RE.sub(" ", title).strip()


def build_text(title_clean, body_clean, max_len=600):
    text = title_clean
    if body_clean:
        text = f"{title_clean} {body_clean}"
    return text[:max_len].strip()


def is_borderline(label, title_clean, has_url):
    """Heuristics for posts worth a human double-check, not a hard rule."""
    if label == "story" and QUESTION_HEUR_RE.search(title_clean):
        return "story title reads as a direct question"
    if label == "ask_hn" and has_url and not QUESTION_HEUR_RE.search(title_clean):
        return "ask_hn post centers on a link rather than a question"
    if label == "show_hn" and not SHOW_HEUR_RE.search(title_clean) and QUESTION_HEUR_RE.search(title_clean):
        return "show_hn title phrased as a question, not an announcement"
    return None


def main():
    with open(IN_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_label = {"ask_hn": [], "show_hn": [], "story": []}
    flagged = []

    for row in rows:
        title_clean = clean_title(row["title"])
        body_clean = clean_html(row["story_text"])
        text = build_text(title_clean, body_clean)

        if len(text) < MIN_TEXT_LEN:
            continue

        label = row["label_source"]
        reason = is_borderline(label, title_clean, bool(row["url"]))
        if reason:
            flagged.append({**row, "title_clean": title_clean, "reason": reason})

        by_label[label].append(
            {
                "id": row["id"],
                "text": text,
                "label": label,
                "permalink": row["permalink"],
            }
        )

    final_rows = []
    for label, items in by_label.items():
        random.shuffle(items)
        final_rows.extend(items[:MAX_PER_LABEL])
    random.shuffle(final_rows)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text", "label", "permalink"])
        writer.writeheader()
        writer.writerows(final_rows)

    with open(REVIEW_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "label_source", "title_clean", "reason", "permalink"]
        )
        writer.writeheader()
        for r in flagged:
            writer.writerow(
                {
                    "id": r["id"],
                    "label_source": r["label_source"],
                    "title_clean": r["title_clean"],
                    "reason": r["reason"],
                    "permalink": r["permalink"],
                }
            )

    print(f"Wrote {len(final_rows)} labeled examples to {OUT_PATH}")
    counts = {}
    for r in final_rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    print("Label distribution:", counts)
    print(f"\nFlagged {len(flagged)} borderline posts for manual review -> {REVIEW_PATH}")


if __name__ == "__main__":
    main()
