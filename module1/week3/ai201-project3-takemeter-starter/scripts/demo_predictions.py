"""
Runs the 5 curated test posts from the README's Sample Classifications
table through the fine-tuned checkpoint and prints label + confidence in a
clean format, for screen recording during the demo video.

Pulls the exact rows (by index in data/test.csv) used in the README table,
rather than hand-retyped/truncated text, so confidence scores match exactly.
"""
import os

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHECKPOINT = os.path.join(ROOT, "takemeter-model", "checkpoint-72")
ID_TO_LABEL = {0: "ask_hn", 1: "show_hn", 2: "story"}

# Substrings used to find the 5 README-table rows in data/test.csv.
POST_MATCHERS = [
    "Should AI be used at all as a total beginner",
    "What's your multi-agent orchestration setup",
    "Jumpjet",
    "Scoundrel Who Steals Fruit",
    "Can you draw a 3 wheeled bicycle",
]

print("Loading fine-tuned TakeMeter model...\n")
tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
model = AutoModelForSequenceClassification.from_pretrained(CHECKPOINT)
model.eval()

test_df = pd.read_csv(os.path.join(ROOT, "data", "test.csv"))

for matcher in POST_MATCHERS:
    row = test_df[test_df["text"].str.contains(matcher, regex=False)].iloc[0]
    text, true_label = row["text"], row["label"]

    inputs = tokenizer(text, truncation=True, max_length=256, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0]
    pred_id = int(torch.argmax(probs).item())
    pred_label = ID_TO_LABEL[pred_id]
    confidence = float(probs[pred_id].item())
    mark = "CORRECT" if pred_label == true_label else "WRONG"

    print(f'POST: "{text[:80]}{"..." if len(text) > 80 else ""}"')
    print(f"  -> predicted: {pred_label}   confidence: {confidence:.1%}   (true: {true_label})  [{mark}]")
    print()
