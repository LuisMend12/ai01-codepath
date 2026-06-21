"""
Zero-shot baseline: classify data/test.csv with Groq's llama-3.3-70b-versatile,
no task-specific training. Evaluated on the exact same test split train.py used.

Saves results/baseline_results.json and results/wrong_predictions_baseline.csv.
"""
import json
import os
import time

import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

load_dotenv()

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")

LABEL_MAP = {"ask_hn": 0, "show_hn": 1, "story": 2}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}

# One example per label, pulled from the training split (never from test.csv)
# so the baseline isn't shown anything it will be evaluated on.
SYSTEM_PROMPT = """You are classifying posts from Hacker News (HN). Assign each post to exactly one of the following categories.

ask_hn: The poster is asking the HN community a direct question or soliciting opinions/advice for themselves. No external link — it's a text-only post.
Example: "What's your go-to queue system? I'm building a product and need something robust for scheduling and retries, but there are so many options (NATS, RabbitMQ, AWS tools) that I can't decide."

show_hn: The poster is showing off something they personally built or made, inviting feedback. The post is about the poster's own creation.
Example: "Remote Exec Server using only Python stdlib — a small tool I built for running commands on remote machines without any third-party dependencies."

story: The poster is sharing third-party content (someone else's article, repo, paper, or announcement) for the community to discuss. The poster did not create the linked content.
Example: "Whitman, switch agents.md files in the CLI — a writeup on a new approach to managing agent config files."

Respond with ONLY the label name: ask_hn, show_hn, or story. Do not explain your reasoning.
"""


def classify(client, text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify this post:\n\n{text}"},
            ],
            temperature=0,
            max_tokens=20,
        )
        raw = response.choices[0].message.content.strip().lower()
        for label in sorted(LABEL_MAP, key=len, reverse=True):
            if raw == label or label in raw:
                return label
        return None
    except Exception as e:
        print(f"API error: {e}")
        return None


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY not set in .env")
    client = Groq(api_key=api_key)

    preds = []
    print(f"Classifying {len(test_df)} test examples with llama-3.3-70b-versatile...")
    for i, row in test_df.iterrows():
        pred = classify(client, row["text"])
        preds.append(pred)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(test_df)} complete...")
        time.sleep(0.1)

    none_count = preds.count(None)
    if none_count:
        print(f"WARNING: {none_count} responses unparseable, excluded from metrics.")

    valid = [(p, t) for p, t in zip(preds, test_df["label_id"]) if p is not None]
    bl_pred_ids = [LABEL_MAP[p] for p, _ in valid]
    bl_true_ids = [t for _, t in valid]

    accuracy = accuracy_score(bl_true_ids, bl_pred_ids)
    label_names = [ID_TO_LABEL[i] for i in range(len(LABEL_MAP))]
    report = classification_report(
        bl_true_ids, bl_pred_ids, target_names=label_names, zero_division=0, output_dict=True
    )
    print(f"\nBaseline accuracy: {accuracy:.3f} (evaluated on {len(valid)}/{len(test_df)})")
    print(classification_report(bl_true_ids, bl_pred_ids, target_names=label_names, zero_division=0))

    cm = confusion_matrix(bl_true_ids, bl_pred_ids, labels=list(range(len(LABEL_MAP))))

    wrong_rows = []
    for idx, (p, t) in enumerate(zip(preds, test_df["label_id"])):
        if p is not None and LABEL_MAP[p] != t:
            wrong_rows.append(
                {
                    "text": test_df.iloc[idx]["text"],
                    "true_label": ID_TO_LABEL[t],
                    "predicted_label": p,
                }
            )
    pd.DataFrame(wrong_rows).to_csv(
        os.path.join(RESULTS_DIR, "wrong_predictions_baseline.csv"), index=False
    )

    results = {
        "model": "llama-3.3-70b-versatile",
        "label_map": LABEL_MAP,
        "test_set_size": len(test_df),
        "unparseable_responses": none_count,
        "accuracy": round(accuracy, 4),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": label_names,
    }
    with open(os.path.join(RESULTS_DIR, "baseline_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {os.path.join(RESULTS_DIR, 'baseline_results.json')}")


if __name__ == "__main__":
    main()
