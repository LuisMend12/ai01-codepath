# TakeMeter — planning.md

## Community

**Hacker News** (via the [Algolia HN Search API](https://hn.algolia.com/api), no auth required).

We started this project targeting r/nba, but Reddit now blocks unauthenticated `.json` access entirely and creating a developer app hit friction mid-session, so we switched communities. Hacker News was chosen because it has free, unauthenticated, full-history access (no rate limits) and — more importantly — because its submission flow already enforces a real, exhaustive, mutually-exclusive taxonomy that the community itself relies on every day.

## Label Taxonomy

HN's own submission mechanism splits every post into one of three structural categories, each with its own dedicated page (`/ask`, `/show`) and its own unwritten norms about what belongs there. We used these three categories directly as our labels rather than inventing a new scheme, because the distinction already matters to anyone who posts or browses HN: regulars know not to post a product launch to `/ask`, and they know `/show` is for "I made this," not "what do you all think about X."

| Label | Definition | Example (title, lightly trimmed) |
|---|---|---|
| `ask_hn` | The OP is posting a text-only submission (no link) to directly ask the community a question or solicit opinions/advice for themselves. | *"What's your go-to queue system?"* — OP is building a product and wants the community's personal recommendations. |
| `show_hn` | The OP is posting something they personally built or made, inviting feedback or interest from the community. Always has a link (or text describing the thing), but the post is about the *OP's own creation*. | *"Show HN: Remote Exec Server using only Python stdlib"* — OP built a tool and is presenting it. |
| `story` | The OP is sharing third-party content (a link to someone else's article, repo, paper, or announcement) for the community to read and discuss. The OP isn't asking for advice about themselves or showing their own work — they're surfacing something else. | *"Whitman, switch agents.md files in the CLI"* (a linked article) — OP didn't write this, they're sharing it. |

**Mutual exclusivity:** Every post is pulled from exactly one of three disjoint Algolia tag pools — `ask_hn`, `show_hn`, or `story`-tagged-but-NOT-`ask_hn`/`show_hn` — so by construction each post has exactly one label (see `scripts/scrape_hn.py`).

**Exhaustiveness:** 100% of collected posts get one of the three labels — there is no fourth "other" bucket. (HN's separate `job` and `poll` item types exist but are excluded entirely at collection time, since they aren't really "discourse" — see README for the exact filtering decision.)

**Anti-shortcut decision:** Both `ask_hn` and `show_hn` posts conventionally start their title with a literal `"Ask HN:"` / `"Show HN:"` prefix. If we left that in, the classifier (and the Groq baseline) could "solve" the task by string-matching the prefix instead of learning anything about how the three kinds of posts are actually written. `scripts/label_dataset.py` strips this prefix before building the model-input `text` field, so the task is genuinely about discourse style (question framing, "I built X" framing, third-party headline framing), not a literal tag.

## Difficult Cases

`scripts/label_dataset.py` heuristically flags posts whose phrasing cuts against their platform-assigned label (e.g. a `story` post whose title is itself a question) into `data/flagged_for_review.csv`. We manually reviewed all of these — see README.md's "Difficult to Label" section for the specific examples and what we decided (in short: we kept the platform's label in every case we checked, because the underlying *structural* signal — text-only ask vs. linked third-party content vs. linked own-work — held up even when the title's surface phrasing looked like a different category).

## Data Collection Plan

**Source:** `scripts/scrape_hn.py` pulls from the Algolia HN Search API (`hn.algolia.com/api/v1/search_by_date`) — public, unauthenticated, no rate limit, full historical depth. We pull the 300 most recent posts under each of the `ask_hn` and `show_hn` tags, plus 300 under the general `story` tag (minus any that double-tagged as `ask_hn`/`show_hn`).

**Per-label target:** Since the label comes directly from which Algolia tag pool a post was pulled from (not a subjective judgment call), the collection step itself can't introduce label noise — the only thing we control is the *count* per label. We targeted enough raw volume per tag to comfortably cap at 90/label (270 total) after dropping anything under 15 characters post-cleaning.

**If a label is underrepresented:** `ask_hn` and `show_hn` are inherently rarer on HN than plain `story` submissions (most of the front page is link-sharing), so the risk is the opposite of the usual case — too few raw `ask_hn`/`show_hn` posts, not too many. If after capping `story` to 90 either `ask_hn` or `show_hn` came in under 90, the plan was to widen the Algolia date window (pull further back in time) for just that tag, since the API has no rate limit and full history — there is no need to ever resort to a synthetic/duplicated example to hit the count.

## Evaluation Metrics

We report **overall accuracy** for both models as the top-line comparison number, but accuracy alone is not enough here: with three roughly-balanced classes, two models can post similar accuracy while failing in completely different, asymmetric ways. We therefore also report:

- **Per-class precision, recall, and F1** — this is the metric that actually surfaces which boundary a model hasn't learned. In our results, the fine-tuned model's `story` recall (0.50) is far below its precision (0.875), meaning it systematically *under*-predicts `story` — a fact totally invisible in the 0.683 accuracy number alone.
- **Confusion matrix** — shows the *direction* of confusion (e.g., `story` predicted as `show_hn` far more often than the reverse), which is more actionable than a precision/recall table alone because it points at which specific label pair needs more/cleaner training examples.

Accuracy answers "how often is the model right." Per-class F1 and the confusion matrix answer "right about what, and wrong in which direction" — for a task whose entire point is distinguishing three specific categories from each other, the second question matters more.

## Definition of Success

For this to be "genuinely useful" as a real triage tool (e.g., auto-routing submissions or flagging mislabeled ones), we set the bar at: fine-tuned accuracy meaningfully above the 33% random-guess floor for a 3-class task, and every per-class F1 ≥ 0.70 (the course's own "model is learning all distinctions well" threshold). "Good enough for deployment" would additionally require the fine-tuned model to beat the zero-shot baseline — if a free, untrained prompt already does the job, fine-tuning isn't earning its complexity for a real tool.

These criteria are specific enough to grade objectively against our actual results (see Evaluation Report in the README): the fine-tuned model reached 0.683 accuracy with one class (`story`, F1 0.636) below the 0.70 bar, and it did **not** beat the baseline (0.829). By our own definition, this model is not yet good enough for deployment — see the Reflection section in the README for why, and what we'd change with more data.

## AI Tool Plan

- **Label stress-testing:** Skipped a separate synthetic stress-test step because our taxonomy isn't built from subjective judgment calls — it's derived directly from HN's own submission mechanism (the `/ask`, `/show` tag pools), so the "edge cases" that matter are real posts where the *platform's* label looks wrong given the title's surface phrasing (see Difficult Cases below and `flagged_for_review.csv`), not hypothetical AI-generated boundary posts.
- **Annotation assistance:** Not used. Labels are assigned deterministically from which Algolia API tag a post was pulled under (`scripts/label_dataset.py`), not from an LLM or human judgment call on each post — there is nothing for an LLM to pre-label, since the ground truth is structural rather than subjective. (Discrepancies between the structural label and surface phrasing were instead handled by the borderline-flagging heuristic and manual review described below.)
- **Failure analysis:** Used Claude (via Claude Code) to help write `scripts/scrape_hn.py`, `label_dataset.py`, `train.py`, `groq_baseline.py`, and `evaluate.py`, and to review the resulting `wrong_predictions_finetuned.csv` for patterns before writing the Reflection section in the README. We verified the suggested pattern (the model leans on first-person "I built/made" framing as a proxy for `show_hn`, and under-predicts `story` when a post lacks any first-person or question framing) by re-reading every one of the 13 misclassified test examples ourselves — see the README's Error Analysis and Reflection sections for the verified conclusions, and the README's AI Usage section for specifics on what we directed the AI to do and what we changed.

## Pipeline

1. `scripts/scrape_hn.py` — pulls raw posts from the Algolia HN Search API into `data/raw_posts.csv`.
2. `scripts/label_dataset.py` — cleans HTML/prefixes, builds the `text` field, balances to a capped count per label, flags borderline cases, writes `data/labeled_dataset.csv`.
3. `scripts/train.py` — splits train/val/test, fine-tunes `distilbert-base-uncased` locally (CPU), evaluates on the test set, saves the confusion matrix and wrong predictions.
4. `scripts/groq_baseline.py` — zero-shot classifies the same test set with `llama-3.3-70b-versatile`.
5. `scripts/evaluate.py` — combines both models' results into the final comparison report.
