"""
Loads the fine-tuned checkpoint and prints prediction + confidence for
every test.csv example, for picking Sample Classifications rows in the README.
"""
import os

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHECKPOINT = os.path.join(ROOT, "takemeter-model", "checkpoint-72")
ID_TO_LABEL = {0: "ask_hn", 1: "show_hn", 2: "story"}

tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
model = AutoModelForSequenceClassification.from_pretrained(CHECKPOINT)
model.eval()

df = pd.read_csv(os.path.join(ROOT, "data", "test.csv"))

for _, row in df.iterrows():
    inputs = tokenizer(row["text"], truncation=True, max_length=256, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0]
    pred_id = int(torch.argmax(probs).item())
    pred_label = ID_TO_LABEL[pred_id]
    confidence = round(float(probs[pred_id].item()), 4)
    correct = "OK" if pred_label == row["label"] else "WRONG"
    print(f"[{correct}] true={row['label']:<8} pred={pred_label:<8} conf={confidence:.4f}  {row['text'][:90]}")
