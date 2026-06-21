"""
Fine-tune distilbert-base-uncased on data/labeled_dataset.csv (local, CPU).

Splits 70/15/15 train/val/test (stratified), tokenizes, fine-tunes, then
evaluates on the held-out test set: accuracy, per-class precision/recall/F1,
confusion matrix, and the specific examples the model got wrong.

Saves train/val/test splits to data/ so groq_baseline.py evaluates on the
exact same test set, and writes results/finetuned_results.json +
results/confusion_matrix.png + results/wrong_predictions_finetuned.csv.
"""
import json
import os

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")

MODEL_NAME = "distilbert-base-uncased"
LABEL_MAP = {"ask_hn": 0, "show_hn": 1, "story": 2}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}
NUM_LABELS = len(LABEL_MAP)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {"accuracy": accuracy_score(labels, predictions)}


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    df = pd.read_csv(os.path.join(DATA_DIR, "labeled_dataset.csv"))
    df["label_id"] = df["label"].map(LABEL_MAP)

    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=42, stratify=df["label_id"]
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=42, stratify=temp_df["label_id"]
    )
    train_df = train_df.reset_index(drop=True)
    val_df = val_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    print(f"Train: {len(train_df)}  Val: {len(val_df)}  Test: {len(test_df)}")

    train_df.to_csv(os.path.join(DATA_DIR, "train.csv"), index=False)
    val_df.to_csv(os.path.join(DATA_DIR, "val.csv"), index=False)
    test_df.to_csv(os.path.join(DATA_DIR, "test.csv"), index=False)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(examples):
        return tokenizer(examples["text"], truncation=True, max_length=256)

    def make_dataset(df_split):
        ds = Dataset.from_pandas(
            df_split[["text", "label_id"]].rename(columns={"label_id": "labels"})
        )
        return ds.map(tokenize, batched=True)

    train_dataset = make_dataset(train_df)
    val_dataset = make_dataset(val_df)
    test_dataset = make_dataset(test_df)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=NUM_LABELS, id2label=ID_TO_LABEL, label2id=LABEL_MAP,
    )

    # ── Hyperparameters ──────────────────────────────────────────────────
    # num_train_epochs=3, learning_rate=2e-5: standard small-dataset BERT
    # fine-tuning defaults. batch_size=8 (not 16) because this runs on CPU,
    # not a T4 GPU — smaller batches keep each step's memory/compute bounded
    # and don't meaningfully hurt convergence at this dataset size (~190
    # training examples => ~24 steps/epoch either way).
    # ─────────────────────────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=os.path.join(ROOT, "takemeter-model"),
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        learning_rate=2e-5,
        weight_decay=0.01,
        warmup_steps=20,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        logging_steps=10,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    print("Starting fine-tuning...")
    trainer.train()
    print("Fine-tuning complete.")

    ft_output = trainer.predict(test_dataset)
    ft_pred_ids = np.argmax(ft_output.predictions, axis=-1)
    ft_true_ids = ft_output.label_ids
    ft_probs = torch.nn.functional.softmax(torch.tensor(ft_output.predictions), dim=-1).numpy()

    ft_accuracy = accuracy_score(ft_true_ids, ft_pred_ids)
    label_names = [ID_TO_LABEL[i] for i in range(NUM_LABELS)]
    report = classification_report(
        ft_true_ids, ft_pred_ids, target_names=label_names, zero_division=0, output_dict=True
    )
    print(f"\nFine-tuned accuracy: {ft_accuracy:.3f}")
    print(classification_report(ft_true_ids, ft_pred_ids, target_names=label_names, zero_division=0))

    cm = confusion_matrix(ft_true_ids, ft_pred_ids)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=label_names)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title("Fine-Tuned DistilBERT — Confusion Matrix (Test Set)")
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "confusion_matrix.png"), dpi=150)
    print(f"Saved confusion matrix -> {os.path.join(RESULTS_DIR, 'confusion_matrix.png')}")

    wrong_idx = np.where(ft_pred_ids != ft_true_ids)[0]
    wrong_rows = []
    for idx in wrong_idx:
        wrong_rows.append(
            {
                "text": test_df.iloc[idx]["text"],
                "true_label": ID_TO_LABEL[ft_true_ids[idx]],
                "predicted_label": ID_TO_LABEL[ft_pred_ids[idx]],
                "confidence": round(float(ft_probs[idx][ft_pred_ids[idx]]), 4),
            }
        )
    pd.DataFrame(wrong_rows).to_csv(
        os.path.join(RESULTS_DIR, "wrong_predictions_finetuned.csv"), index=False
    )
    print(f"Wrong predictions: {len(wrong_idx)} / {len(ft_true_ids)}")

    results = {
        "model": MODEL_NAME,
        "label_map": LABEL_MAP,
        "test_set_size": len(test_df),
        "accuracy": round(ft_accuracy, 4),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": label_names,
    }
    with open(os.path.join(RESULTS_DIR, "finetuned_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {os.path.join(RESULTS_DIR, 'finetuned_results.json')}")


if __name__ == "__main__":
    main()
