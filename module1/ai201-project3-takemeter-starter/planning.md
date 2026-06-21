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

## Pipeline

1. `scripts/scrape_hn.py` — pulls raw posts from the Algolia HN Search API into `data/raw_posts.csv`.
2. `scripts/label_dataset.py` — cleans HTML/prefixes, builds the `text` field, balances to a capped count per label, flags borderline cases, writes `data/labeled_dataset.csv`.
3. `scripts/train.py` — splits train/val/test, fine-tunes `distilbert-base-uncased` locally (CPU), evaluates on the test set, saves the confusion matrix and wrong predictions.
4. `scripts/groq_baseline.py` — zero-shot classifies the same test set with `llama-3.3-70b-versatile`.
5. `scripts/evaluate.py` — combines both models' results into the final comparison report.
