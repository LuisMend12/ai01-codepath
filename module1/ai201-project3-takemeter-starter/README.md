# TakeMeter — Hacker News Post Classifier

Fine-tunes `distilbert-base-uncased` to classify Hacker News posts into three discourse categories the community already uses (`ask_hn`, `show_hn`, `story`), and compares it against a zero-shot Groq `llama-3.3-70b-versatile` baseline on the same held-out test set.

## What's Included

```
ai201-project3-takemeter-starter/
├── data/
│   ├── raw_posts.csv             # 847 raw posts pulled from the Algolia HN API
│   ├── flagged_for_review.csv    # 15 borderline posts surfaced for manual review
│   ├── labeled_dataset.csv       # 270 final labeled examples (90/90/90)
│   ├── train.csv / val.csv / test.csv  # 70/15/15 stratified split (189/40/41)
├── scripts/
│   ├── scrape_hn.py               # Collect raw posts (Algolia HN Search API, no auth)
│   ├── label_dataset.py           # Clean text, assign labels, flag borderline cases
│   ├── train.py                   # Fine-tune DistilBERT locally (CPU), evaluate on test set
│   ├── groq_baseline.py           # Zero-shot classification with llama-3.3-70b-versatile
│   └── evaluate.py                # Combine both models' results into a comparison
├── results/
│   ├── confusion_matrix.png               # Fine-tuned model, test set
│   ├── finetuned_results.json             # Fine-tuned metrics
│   ├── baseline_results.json              # Baseline metrics
│   ├── comparison.json                    # Side-by-side comparison
│   ├── wrong_predictions_finetuned.csv    # Every test example the fine-tuned model missed
│   └── wrong_predictions_baseline.csv     # Every test example the baseline missed
├── planning.md                    # Label taxonomy, definitions, examples
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows; use bin/activate on macOS/Linux
pip install -r requirements.txt
```

Set your Groq key in `.env` (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

`scrape_hn.py` needs no credentials — the Algolia HN Search API is fully public.

## Running the Pipeline

```bash
python scripts/scrape_hn.py        # -> data/raw_posts.csv
python scripts/label_dataset.py    # -> data/labeled_dataset.csv, data/flagged_for_review.csv
python scripts/train.py            # -> data/{train,val,test}.csv, results/finetuned_*
python scripts/groq_baseline.py    # -> results/baseline_*
python scripts/evaluate.py         # -> results/comparison.json
```

---

## Community and Why It Changed Mid-Project

We originally targeted r/nba, but Reddit now returns `403` on every unauthenticated `.json` request (confirmed directly — not a header/User-Agent issue), and finishing a developer-app signup mid-session added friction without a clear payoff. We switched to **Hacker News**, accessed through the [Algolia HN Search API](https://hn.algolia.com/api) — fully public, no auth, no rate limits, and full historical depth (we don't depend on whatever happens to be on the front page right now).

## Label Taxonomy

Full definitions and examples are in [planning.md](planning.md). Summary:

| Label | Definition |
|---|---|
| `ask_hn` | Text-only post where the OP directly asks the community a question or solicits advice for themselves. |
| `show_hn` | The OP is presenting something they personally built, inviting feedback. |
| `story` | The OP is sharing third-party content (someone else's link) for the community to discuss. |

These three categories come directly from how HN's own submission flow already splits posts (the `/ask` and `/show` pages exist because the community treats these as genuinely different kinds of posts) — we didn't invent a new scheme, we used theirs. They're **mutually exclusive** by construction (each post is pulled from exactly one of three disjoint API tag pools) and **exhaustive**: 100% of the 270 examples in `labeled_dataset.csv` carry one of the three labels, with no "other" bucket. (HN `job` and `poll` item types are excluded entirely at collection time — see `scrape_hn.py` — since they aren't discourse in the relevant sense; in practice they're a small fraction of all posts.)

**Avoiding a trivial shortcut:** `ask_hn`/`show_hn` posts conventionally start their title with a literal `"Ask HN:"` / `"Show HN:"` prefix. `label_dataset.py` strips this before building the model's `text` field — otherwise both the classifier and the Groq baseline could "solve" the task with a substring match instead of learning anything about how the three kinds of posts are actually phrased.

## Data Collection

Collected via `scripts/scrape_hn.py` from the Algolia HN Search API (`hn.algolia.com/api/v1/search_by_date`), pulling the 300 most recent posts under each of the `ask_hn` and `show_hn` tags, plus 300 posts under the general `story` tag (filtered down to 247 after excluding any that were also tagged `ask_hn`/`show_hn`) — 847 raw posts total, all from June 2026.

## Labeling Process

`scripts/label_dataset.py`:
1. Strips the `"Ask HN:"` / `"Show HN:"` / `"Tell HN:"` title prefix and HTML-unescapes/strips tags from the post body.
2. Builds the model-input `text` field as cleaned title + cleaned body (truncated to 600 characters).
3. Drops anything under 15 characters after cleaning.
4. Assigns the label directly from which API tag pool the post came from (see Label Taxonomy above) — this is the same idea as labeling Reddit posts by their flair, except HN's tagging is part of the submission mechanism itself rather than an optional flair.
5. Caps each label at 90 examples (randomly sampled) so the final dataset is exactly balanced and CPU fine-tuning stays fast, then writes `labeled_dataset.csv` (270 rows).
6. Flags structurally-borderline posts (e.g. a `story` whose title is itself a question) into `flagged_for_review.csv` for manual inspection.

**Label distribution** (final, balanced by construction):

| Label | Count |
|---|---|
| `ask_hn` | 90 |
| `show_hn` | 90 |
| `story` | 90 |
| **Total** | **270** |

Split 70/15/15 (stratified): train 189 (63/63/63), val 40 (14/13/13), test 41 (13/14/14).

### Difficult to Label

`label_dataset.py` flagged 15 posts whose title phrasing cut against their platform-assigned label. We reviewed all of them; here are three representative cases and what we decided:

1. **"Is Trump-Netanyahu Rift on the Cards?"** — labeled `story`, but the title is itself phrased as a question, which is the surface pattern we'd expect from `ask_hn`. Checking the raw data, this post has a `url` (a news article) and no `story_text` — it's a link submission of a news headline written in the rhetorical-question style common in journalism, not the OP asking HN anything. **Decision: kept `story`.** The structural signal (has a URL, OP isn't asking for anything personally) matters more than the surface phrasing.

2. **"Can someone try to get my websites admin panel?"** — labeled `story`, and arguably the most ask-like phrasing in the flagged set ("can someone..." directly addresses the community). It also has a `url` (`https://gag.gg/`) and no body text. **Decision: kept `story`.** It's structurally a link submission (probably what HN itself would call a "story"), even though the title imperative reads like a request the way an `ask_hn` post would. We noted this as a genuine boundary case rather than a mislabel — the taxonomy's edge is "is the OP soliciting something for themselves vs. presenting a link," and this post sits closer to that edge than most.

3. **"Can you draw a 3 wheeled bicycle?"** — labeled `show_hn` (links to `doodle.wtf/?prompt=...`, an AI drawing tool the OP built). The question framing is a "try my tool" hook, not a request for advice. **Decision: kept `show_hn`.** This is also the single example both the fine-tuned model and the baseline got wrong (predicted `ask_hn`) — see Error Analysis below, since the surface form really did fool both models the same way it could fool a human skimming the title alone.

## Model and Training

**Base model:** `distilbert-base-uncased` (66M params), loaded via `AutoModelForSequenceClassification` with a 3-way classification head.

**Training approach:** Standard fine-tuning with Hugging Face `Trainer` — train on `train.csv`, select the best checkpoint by validation accuracy across 3 epochs, evaluate once on the untouched `test.csv`.

**Key hyperparameter decisions** (`scripts/train.py`):
- `learning_rate=2e-5` — the standard starting point for BERT-family fine-tuning; not tuned further given the dataset size.
- `num_train_epochs=3` — kept at the course-recommended default for a ~200-example dataset; more epochs risked overfitting a training set this small.
- `per_device_train_batch_size=8` (not the notebook's GPU default of 16) — **this run executes on CPU, not a T4 GPU**, so batch size was halved to keep per-step memory/compute bounded. With only ~189 training examples (~24 steps/epoch either way), this had no meaningful effect on convergence — training completed in under 4 minutes.

## Baseline: Zero-Shot Groq

`scripts/groq_baseline.py` prompts `llama-3.3-70b-versatile` (temperature 0) with the three label definitions from `planning.md` plus one example per label pulled from the **training** split (never from `test.csv`), and asks for just the label name. All 41 test responses parsed cleanly into one of the three valid labels (0 unparseable).

---

## Evaluation Report

Both models evaluated on the same 41-example test set.

### Overall Accuracy

| Model | Accuracy |
|---|---|
| Zero-shot baseline (Groq `llama-3.3-70b-versatile`) | **0.829** |
| Fine-tuned `distilbert-base-uncased` | 0.683 |

The zero-shot baseline outperformed the fine-tuned model by 14.6 points — see Reflection below.

### Per-Class F1

| Label | Fine-tuned F1 | Baseline F1 |
|---|---|---|
| `ask_hn` | 0.733 | 0.833 |
| `show_hn` | 0.667 | 0.769 |
| `story` | 0.636 | 0.875 |

### Confusion Matrices

Rows = true label, columns = predicted label, order `[ask_hn, show_hn, story]`.

**Fine-tuned DistilBERT** (also saved as [results/confusion_matrix.png](results/confusion_matrix.png)):

| true \ pred | ask_hn | show_hn | story |
|---|---|---|---|
| **ask_hn** | 11 | 1 | 1 |
| **show_hn** | 4 | 10 | 0 |
| **story** | 2 | 5 | 7 |

**Zero-shot baseline (Groq):**

| true \ pred | ask_hn | show_hn | story |
|---|---|---|---|
| **ask_hn** | 10 | 2 | 1 |
| **show_hn** | 1 | 10 | 3 |
| **story** | 0 | 0 | 14 |

### Error Analysis

**1. Fine-tuned model: `"Scion: A next-generation inter-domain routing architecture"` — true `story`, predicted `show_hn` (confidence 0.376, the lowest-confidence error in the whole set).**
This title has no first-person framing ("I built/made") and no question mark — there's almost no lexical signal at all for a model trained on only 63 `story` examples. With this little training data, DistilBERT appears to have leaned on "sounds like a polished technical project name" as a weak proxy for `show_hn`, which fails on `story` posts (like this one, an academic project being shared by someone other than its creator) that happen to have similarly technical-sounding titles.

**2. Fine-tuned model: `"Self-hostable academic paper manager (linxiv) — ... I wanna show off and ask for feedback on my project..."` — true `show_hn`, predicted `ask_hn` (confidence 0.554).**
The body literally contains "ask for feedback," which is a real, defensible ask-like signal — this post genuinely blends both intents (showing a project *and* asking for feedback on it), and 0.554 is a low-confidence call, not a clear miss. This is a case where the taxonomy's boundary is genuinely fuzzy, not a model failure.

**3. Both models: `"Can you draw a 3 wheeled bicycle?"` — true `show_hn`, predicted `ask_hn` (fine-tuned, confidence 0.521) and `ask_hn` (baseline).**
Every other cue is missing: no first-person "I built" framing, just a question, which is exactly the surface pattern `ask_hn` is defined by. This is the same case flagged as borderline during labeling (see above) — both models made the same mistake a human skimming only the title would likely make.

**4. Baseline: `"Anthropic pauses credit change for Claude Code — Quoting from an email they sent: ..."` — true `ask_hn`, predicted `story`.**
This post quotes a third-party email rather than asking a direct question, so it reads like someone sharing an announcement (`story`) rather than asking for something. Unlike most `ask_hn` posts, it has no interrogative sentence at all — the baseline's zero-shot prompt leans heavily on "does this look like a question," and this is a real `ask_hn` post that doesn't.

### Reflection: What the Model Learned vs. What We Intended

We intended both models to learn the **structural distinction** HN's own submission flow encodes: is the OP requesting something for themselves (`ask_hn`), presenting their own work (`show_hn`), or relaying someone else's content (`story`)? Stripping the literal "Ask HN:"/"Show HN:" prefix was specifically meant to force this — without it, the prefix string alone would solve the task.

What the **fine-tuned model** actually learned, with only 63 examples per class, looks more like a shallow lexical proxy for that distinction: first-person verbs ("I built," "I made") strongly predict `show_hn` (it had no trouble with `linxiv`-style posts once that framing was present), and the *absence* of obvious self-referential or question framing tends to fall back to whichever class is lexically closest, which is why `story` was confused most often: its precision was higher than its recall (0.50), meaning the model under-predicts `story` — it's “too eager” to call ambiguous, plainly-worded technical headlines `show_hn` instead. The relatively small, capped (90/label) training set is almost certainly why: DistilBERT didn't see enough lexical variety within `story` to learn that "plain technical headline with no self-reference" is its dominant pattern, rather than an edge case.

The **zero-shot Groq baseline** outperforming a fine-tuned model is the most notable result here, and it makes sense given the dataset size: a 70B-parameter model already has a rich prior over what "someone asking a question" vs. "someone announcing their own project" vs. "a news headline" sound like, built from vastly more text than 189 fine-tuning examples could ever provide. Its one clear failure mode (`ask_hn` → `story` when no question mark/interrogative is present, as in the Anthropic-email example) shows it's leaning on roughly the same shallow "is this a question" heuristic as DistilBERT, but its much larger pretraining prior makes that heuristic correct far more often. Both models converge on the same kind of mistake when a post defies the typical phrasing for its category (the "3 wheeled bicycle" example) — which suggests the actual remaining difficulty isn't model capacity, it's that a meaningful minority of real HN posts are genuinely ambiguous between two categories, not cleanly separable by either model.
