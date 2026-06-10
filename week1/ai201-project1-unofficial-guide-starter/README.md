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

**Chunk size:** 1,600 characters (~400 tokens at ~4 chars/token)

**Overlap:** 200 characters (~50 tokens)

**Why these choices fit your documents:**

The corpus has two structurally different document types. The three GitHub guides are long-form, section-structured Markdown: an H2 section like "Arrays" or "Caching" can span hundreds of lines, so a purely character-based split would cut across headings mid-thought. The splitter uses a recursive boundary-aware strategy — it tries `\n## `, then `\n### `, then `\n\n`, then `\n`, then `. ` in that order before falling back to raw character splits — so structural boundaries are respected as long as a section fits within the limit.

The Reddit posts are conversational and paragraph-driven. Each paragraph typically expresses one opinion or tip (100–200 tokens), so a 1,600-character ceiling naturally captures 1–3 paragraphs per chunk — focused enough to embed a single idea, large enough to avoid over-fragmentation.

The 200-character overlap addresses a common Reddit pattern: an engineer sets up context in one paragraph ("I bombed every Google loop for two years...") and delivers the actionable advice in the next. Without overlap, a chunk boundary at that seam yields two incomplete thoughts. 200 characters (~2 sentences) carries enough setup without duplicating large amounts of guide text across neighbors.

**Final chunk count:** Run `python chunk_and_embed.py` — the script prints per-file chunk counts and a total at the end. (Fill this in after running.)

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (local, no API key required)

**Production tradeoff reflection:**

`all-MiniLM-L6-v2` runs entirely on CPU, costs nothing, and keeps data local — strong defaults for a class project. Its 256-token context window is tight for 400-token chunks, but sentence-transformers truncates gracefully, and the first 256 tokens of a passage carry most of its semantic content.

For a production system I would weigh four tradeoffs:

- **Domain accuracy:** This model was trained on general text. Interview jargon (FAANG, TC, YOE, OA, LC hard) may not be tightly clustered in its embedding space. A bi-encoder fine-tuned on Stack Overflow or tech Q&A would improve precision on domain vocabulary, at the cost of a more complex training pipeline.
- **Context length:** OpenAI `text-embedding-3-small` supports 8,191 tokens. That would allow larger chunks for the GitHub guides — capturing a full subsection in one vector rather than splitting it — and would eliminate the truncation problem entirely.
- **Cost vs. privacy:** API-hosted embeddings (OpenAI, Cohere) add per-token cost and send document text to a third party. For a guide built from public GitHub repos and Reddit that tradeoff is acceptable, but for a corpus of internal docs or proprietary interviews it would not be.
- **Multilingual support:** Not relevant here, but if the guide needed to serve non-English speakers, `multilingual-e5-large` or Cohere's `embed-multilingual-v3.0` would be the switch without rewriting the rest of the pipeline.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

```
You are a tech job interview advisor. You must follow these rules without exception:

1. Answer using ONLY information found in the context passages below.
   Never draw on your training data or general knowledge.
2. After every factual claim, cite the source file in brackets.
   Example: "Practice arrays and linked lists first [coding_interview_university.txt]."
3. If the context passages do not contain enough information to answer the question,
   respond exactly: "My sources don't cover this — I can only answer based on the
   retrieved documents."
4. End every response with a "Sources:" section listing, one per line,
   the filename and URL of each document you drew from.
```

Rule 1 prevents the model from using its training knowledge. Rule 3 gives it an explicit safe exit so it doesn't hallucinate when retrieval misses. Both rules are stated as "must" and "without exception" rather than "try to" — softer language leaves room for the model to rationalize reaching beyond the context.

The retrieved chunks are formatted with a file name and source URL header before each passage so the model can write accurate citations without fabricating them:

```
[Passage 1]
File: coding_interview_university.txt
Source URL: https://github.com/jwasham/coding-interview-university

<chunk text>
```

**How source attribution is surfaced in the response:**

Two mechanisms work together. First, the model is instructed to add `[filename.txt]` inline after every claim, making citations part of the prose. Second, `app.py` independently extracts the `filename` and `source` metadata from every retrieved chunk and renders them as a separate "Retrieved sources" panel in the Gradio UI — so attribution is visible even if the model's inline citation is imprecise. The UI panel also shows the cosine similarity score for each source so it's clear how confident the retrieval was.

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

## Stretch Feature: Hybrid Search

<!-- Run each of the 5 Evaluation Plan questions in both "Hybrid" and "Semantic only"
     mode (toggle in the Gradio UI) and record what changed. -->

**Approach:**

The app builds a `BM25Okapi` keyword index over the same chunks stored in ChromaDB
(pulled via `collection.get()` at startup — no separate index file). For each query,
two ranked lists are computed:

- **Semantic:** top-15 chunks by cosine similarity from ChromaDB
- **Keyword (BM25):** top-15 chunks by BM25 score over tokenized chunk text

These are combined with **Reciprocal Rank Fusion** (`score = Σ 1 / (60 + rank + 1)`
across both lists), and the fused top-5 are passed to the LLM. RRF is used instead of
a weighted score blend because BM25 scores and cosine distances aren't on comparable
scales — RRF only needs each retriever's ranking. The Gradio UI has a "Retrieval mode"
toggle (Hybrid / Semantic only) so the same question can be compared side-by-side, and
each retrieved source is tagged with `(matched via: semantic)`, `(matched via: keyword)`,
or `(matched via: keyword+semantic)`.

**Comparison results:**

| # | Question | Semantic-only sources | Hybrid sources | Answer changed? | Notes |
|---|----------|------------------------|-----------------|------------------|-------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Which performed better, and why:**

<!-- Fill in after running both modes. Look specifically for:
     - Queries containing exact jargon (e.g. "two-pointer", "FAANG", a company name)
       where BM25 likely surfaced a chunk semantic search ranked lower
     - Queries that are paraphrases of document language, where semantic search
       likely outperforms BM25
     - Whether the fused top-5 ever dropped a chunk that semantic-only retrieval
       had ranked highly, and whether that hurt the answer -->

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

- *What I gave the AI:* The Chunking Strategy section from planning.md (chunk size 1,600 chars / 200 char overlap, recursive boundary-aware splitting rationale, two-document-type reasoning) and the Architecture diagram showing the five pipeline stages.
- *What it produced:* `chunk_and_embed.py` with `_recursive_split()` using the separator priority list `["\n## ", "\n### ", "\n\n", "\n", ". "]`, `_add_overlap()` that prepends the tail of the previous chunk, and a `main()` that drops and rebuilds the ChromaDB collection on each run.
- *What I changed or overrode:* The initial draft used `text.split(sep)` which consumed the separator and silently dropped heading markers from chunk text. I changed it to `re.split(re.escape(sep), text)` and verified that H2 headings survived into their chunk's text so the embedding would include the section title.

**Instance 2**

- *What I gave the AI:* The grounding rules from the AI Tool Plan section ("answer using ONLY information in context passages, cite filename inline, safe exit when context is insufficient") and the Evaluation Plan's 5 test questions as example queries to design the interface around.
- *What it produced:* `app.py` with the four-rule system prompt, a `answer_question()` function that returns `(answer, sources_markdown)` as separate outputs, and a two-column Gradio layout with an answer box and a retrieved-sources panel.
- *What I changed or overrode:* The first draft set `temperature=0.7`. I lowered it to `0.2` because grounded generation should be deterministic — higher temperature increases the chance the model rephrases retrieved facts in ways that subtly introduce inaccuracies. I also added the similarity score to the sources panel (not in the original output) so it's easy to spot when retrieval confidence is low during evaluation.
