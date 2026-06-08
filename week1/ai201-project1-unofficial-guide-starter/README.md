# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

Tech job interview tips — the unofficial, peer-sourced knowledge that engineers share
with each other on forums and open-source guides, but that you cannot get from any
company's official recruiting page. This includes what LeetCode patterns actually show
up in FAANG-style interviews, what matters in system design rounds, how to negotiate
an offer, and what experienced engineers wish they had known before interviewing.
This knowledge is valuable because it closes the gap between "what the JD says" and
"what you actually need to do to pass."

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | coding-interview-university | GitHub README | https://github.com/jwasham/coding-interview-university |
| 2 | system-design-primer | GitHub README | https://github.com/donnemartin/system-design-primer |
| 3 | tech-interview-handbook | GitHub README | https://github.com/yangshun/tech-interview-handbook |
| 4 | r/cscareerquestions — top post 1 | Reddit self-post + comments | documents/reddit_cscareerquestions_01.txt |
| 5 | r/cscareerquestions — top post 2 | Reddit self-post + comments | documents/reddit_cscareerquestions_02.txt |
| 6 | r/cscareerquestions — top post 3 | Reddit self-post + comments | documents/reddit_cscareerquestions_03.txt |
| 7 | r/cscareerquestions — top post 4 | Reddit self-post + comments | documents/reddit_cscareerquestions_04.txt |
| 8 | r/cscareerquestions — top post 5 | Reddit self-post + comments | documents/reddit_cscareerquestions_05.txt |
| 9 | r/leetcode — top post 1 | Reddit self-post + comments | documents/reddit_leetcode_06.txt |
| 10 | r/leetcode — top post 2 | Reddit self-post + comments | documents/reddit_leetcode_07.txt |

---

## Document Ingestion Pipeline

The pipeline is implemented in [ingest.py](ingest.py). Run it once to populate the
`documents/` folder before chunking:

```
pip install -r requirements.txt
python ingest.py
```

**Stage 1 — GitHub READMEs (3 documents)**

The script fetches the raw Markdown of three widely-cited, community-maintained
interview prep repos using GitHub's `raw.githubusercontent.com` endpoint. No API
key is needed. Each file is then cleaned with `clean_github_markdown()`:

- Badge links (`[![alt](img)](href)`) are stripped — they are just navigation.
- HTML comments (`<!-- ... -->`) and inline HTML tags are removed.
- Markdown table separator rows (`|---|---|`) are deleted since they add no meaning.
- Three or more consecutive blank lines are collapsed to two.

Very large READMEs (the system-design-primer README is ~80 k characters) are
truncated to 35,000 characters to produce chunks of manageable size later.

**Stage 2 — Reddit posts (7 documents)**

The script calls `https://www.reddit.com/r/<subreddit>/top.json?t=all` — Reddit's
public JSON API, no authentication required. It over-fetches (4× the target limit)
and filters to self-posts whose body text is at least 200 characters, discarding
link posts and near-empty posts. For each post it then fetches the thread JSON to
collect top-scored comments (score ≥ 10), cleaned with `clean_reddit_text()`:

- HTML entities (`&amp;`, `&lt;`, etc.) are decoded.
- Zero-width spaces (`&#x200B;`) inserted by Reddit's editor are removed.
- Bare URLs are replaced with `[link]` so the surrounding sentence still reads
  naturally but raw URLs don't pollute the embeddings.
- Deleted or removed posts/comments are discarded entirely.

Each document is saved as a UTF-8 `.txt` file with a one-line `Source:` header,
followed by a separator, followed by the cleaned text. The source line provides
attribution that can later be surfaced in generated responses.

A 1.5-second delay is inserted between requests to respect Reddit's rate limit.

**Output structure**

```
documents/
  coding_interview_university.txt    # GitHub README
  system_design_primer.txt           # GitHub README
  tech_interview_handbook.txt        # GitHub README
  reddit_cscareerquestions_01.txt    # Reddit post + top comments
  reddit_cscareerquestions_02.txt
  ...
  reddit_leetcode_06.txt
  reddit_leetcode_07.txt
```

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**

**Overlap:**

**Why these choices fit your documents:**

**Final chunk count:**

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
