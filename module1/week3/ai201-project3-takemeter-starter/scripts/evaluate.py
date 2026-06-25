"""
Combine results/finetuned_results.json and results/baseline_results.json
into a single side-by-side comparison, printed to stdout and saved to
results/comparison.json. The narrative writeup (error analysis, reflection)
lives in README.md — this script just assembles the numbers it's based on.
"""
import json
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def load(name):
    with open(os.path.join(RESULTS_DIR, name)) as f:
        return json.load(f)


def main():
    ft = load("finetuned_results.json")
    bl = load("baseline_results.json")

    print("=" * 60)
    print("RESULTS COMPARISON (same test set, n =", ft["test_set_size"], ")")
    print("=" * 60)
    print(f"{'Model':<35}{'Accuracy':>10}")
    print("-" * 45)
    print(f"{'Zero-shot baseline (Groq llama-3.3-70b)':<35}{bl['accuracy']:>10.3f}")
    print(f"{'Fine-tuned distilbert-base-uncased':<35}{ft['accuracy']:>10.3f}")
    print("-" * 45)

    print("\nPer-class F1:")
    print(f"{'Label':<12}{'Fine-tuned':>12}{'Baseline':>12}")
    for label in ft["confusion_matrix_labels"]:
        ft_f1 = ft["classification_report"][label]["f1-score"]
        bl_f1 = bl["classification_report"][label]["f1-score"]
        print(f"{label:<12}{ft_f1:>12.3f}{bl_f1:>12.3f}")

    comparison = {
        "test_set_size": ft["test_set_size"],
        "finetuned_accuracy": ft["accuracy"],
        "baseline_accuracy": bl["accuracy"],
        "finetuned_per_class": {
            label: ft["classification_report"][label] for label in ft["confusion_matrix_labels"]
        },
        "baseline_per_class": {
            label: bl["classification_report"][label] for label in bl["confusion_matrix_labels"]
        },
        "finetuned_confusion_matrix": ft["confusion_matrix"],
        "baseline_confusion_matrix": bl["confusion_matrix"],
        "labels": ft["confusion_matrix_labels"],
    }
    with open(os.path.join(RESULTS_DIR, "comparison.json"), "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\nSaved {os.path.join(RESULTS_DIR, 'comparison.json')}")


if __name__ == "__main__":
    main()
