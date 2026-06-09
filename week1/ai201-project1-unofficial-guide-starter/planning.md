# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

Tech job interview tips — the unofficial, experience-based knowledge that engineers share
with each other on forums and in open-source guides, but that you cannot find in any
company's recruiting FAQ. This covers what LC problems actually come up, what system
design interviewers care about, how to negotiate, and what practicing engineers wish
they had known before interviewing at FAANG/top companies.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | coding-interview-university (GitHub) | Massive self-taught study plan by a dev who got into Amazon | https://github.com/jwasham/coding-interview-university |
| 2 | system-design-primer (GitHub) | Community-curated system design interview guide | https://github.com/donnemartin/system-design-primer |
| 3 | tech-interview-handbook (GitHub) | Algorithms, behavioral, and salary negotiation advice | https://github.com/yangshun/tech-interview-handbook |
| 4 | r/cscareerquestions — top post 1 | High-voted self-post on interview experiences/advice | https://reddit.com/r/cscareerquestions (dynamically fetched) |
| 5 | r/cscareerquestions — top post 2 | High-voted self-post on interview experiences/advice | https://reddit.com/r/cscareerquestions (dynamically fetched) |
| 6 | r/cscareerquestions — top post 3 | High-voted self-post on interview experiences/advice | https://reddit.com/r/cscareerquestions (dynamically fetched) |
| 7 | r/cscareerquestions — top post 4 | High-voted self-post on interview experiences/advice | https://reddit.com/r/cscareerquestions (dynamically fetched) |
| 8 | r/cscareerquestions — top post 5 | High-voted self-post on interview experiences/advice | https://reddit.com/r/cscareerquestions (dynamically fetched) |
| 9 | r/leetcode — top post 1 | High-voted self-post on LC strategy and interview prep | https://reddit.com/r/leetcode (dynamically fetched) |
| 10 | r/leetcode — top post 2 | High-voted self-post on LC strategy and interview prep | https://reddit.com/r/leetcode (dynamically fetched) |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 400 tokens (~1,600 characters)

**Overlap:** 50 tokens (~200 characters)

**Reasoning:**

The corpus has two structurally different document types that pull in opposite directions:

- **Long-form GitHub guides** (coding-interview-university, system-design-primer, tech-interview-handbook): These are dense, structured documents with H2/H3 section headings. A single section can span hundreds of lines (e.g., "Arrays" or "System Design: Scaling"). Splitting purely by character count would cut across headings and leave orphaned context. The splitting strategy uses a **recursive splitter** that first breaks on headings (`##`, `###`), then paragraph breaks (`\n\n`), then sentences — so structural boundaries are respected before falling back to raw size.

- **Reddit posts** (r/cscareerquestions, r/leetcode): These are conversational, paragraph-driven posts where a single paragraph usually contains one coherent opinion or tip. Paragraphs are shorter (often 100–200 tokens), so a 400-token ceiling naturally captures 1–3 paragraphs per chunk — enough context without diluting the retrieval signal with unrelated advice from the same post.

**Why 400 tokens specifically:** Small enough that Reddit paragraphs remain focused and don't blend unrelated tips, but large enough that system design explanations (which build across multiple sentences) stay coherent. Models like `text-embedding-3-small` support up to 8,191 tokens, so 400 tokens is well within range and produces embeddings that represent one idea cleanly.

**Why 50-token overlap:** Reddit posts frequently set up context in one paragraph and deliver the punchline in the next ("I bombed the Amazon loop... here's what I'd do differently"). Without overlap, a chunk boundary at that seam produces two useless half-ideas. 50 tokens (~2–3 sentences) is enough to carry that setup without duplicating large amounts of guide text across neighboring chunks.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers`

**Top-k:** 5

**Production tradeoff reflection:**

`all-MiniLM-L6-v2` is a strong default for a class project: it runs locally with no API key, produces 384-dimension vectors, and is fast enough to embed thousands of chunks in seconds on a CPU. Its context window is 256 tokens, which is fine for our 400-token chunks (sentence-transformers silently truncates; the first 256 tokens carry most of the meaning in a passage).

For a real deployed system I would weigh:

- **Accuracy on domain-specific text:** `all-MiniLM-L6-v2` was trained on general text. Interview-domain jargon (FAANG, LC, OA, SWE, TC, YOE) may not map well in its embedding space. A model fine-tuned on tech Q&A (e.g., OpenAI `text-embedding-3-small` or a domain-fine-tuned bi-encoder) would improve retrieval precision at the cost of adding an API dependency.
- **Context length:** OpenAI `text-embedding-3-small` supports 8,191 tokens. That would let us use larger chunks for the long GitHub guides without truncation, capturing more of a section's reasoning in one vector.
- **Cost vs. local:** API-hosted embeddings (OpenAI, Cohere) cost money per token but require no GPU. A local model like `all-MiniLM-L6-v2` or `nomic-embed-text` is free and keeps data private — important if the corpus contained proprietary material.
- **Multilingual:** Not a concern here, but Cohere's `embed-multilingual-v3.0` or `multilingual-e5-large` would be the switch if the guide needed to serve non-English users.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | What data structures does coding-interview-university say to study first? | Arrays, linked lists, hash tables, stacks, and queues are listed as the foundational structures to master before moving to trees and graphs. |
| 2 | What system design topics come up most in FAANG-style interviews according to the system-design-primer? | Load balancing, caching (CDN, Redis), database replication/sharding, horizontal vs. vertical scaling, and CAP theorem are the most frequently cited topics. |
| 3 | What do people on r/cscareerquestions recommend when negotiating a job offer? | Don't reveal your current salary or accept on the spot; have a competing offer if possible; negotiate total comp (equity, signing bonus) not just base; and let the recruiter make the first number. |
| 4 | How many LeetCode problems should someone complete before a FAANG coding interview? | Community consensus is roughly 100–300 problems with a focus on medium difficulty. Quality of understanding patterns (sliding window, two pointers, BFS/DFS, DP) matters more than raw count. |
| 5 | What behavioral interview questions come up most often at top tech companies? | "Tell me about a time you failed," conflict with a teammate, most challenging project, and a time you showed leadership or influenced without authority are the most common categories. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. **Reddit posts are noisy and context-dependent.** A Reddit post's most useful sentence is often a reply to a now-deleted comment, or assumes the reader saw the original post title. After chunking, that sentence lands in a chunk with no surrounding context, so the embedding captures something like "this worked for me" with no referent. The retrieval may surface that chunk for unrelated queries.

2. **Long GitHub READMEs get truncated.** `ingest.py` caps each GitHub document at 35,000 characters to keep chunk counts manageable. The tech-interview-handbook's negotiation and behavioral sections appear later in its README and may be cut off entirely, causing Q3 and Q5 to return no relevant chunks even though the source document covers those topics.

---

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐
│  Document Ingestion │    │       Chunking        │    │  Embedding + Vector Store│
│                     │    │                       │    │                          │
│  ingest.py          │───▶│  chunk_and_embed.py   │───▶│  chunk_and_embed.py      │
│  requests library   │    │  recursive_split()    │    │  sentence-transformers   │
│  GitHub raw API     │    │  400 chars / 200 ovlp │    │  all-MiniLM-L6-v2        │
│  Reddit JSON API    │    │  ~N total chunks      │    │  ChromaDB (persistent)   │
└─────────────────────┘    └──────────────────────┘    └──────────┬───────────────┘
                                                                   │
                           ┌──────────────────────┐    ┌──────────▼───────────────┐
                           │      Generation       │    │        Retrieval          │
                           │                       │    │                          │
                           │  app.py               │◀───│  app.py                  │
                           │  Groq API             │    │  ChromaDB cosine query   │
                           │  llama-3.3-70b        │    │  top-5 chunks            │
                           │  grounding prompt     │    │                          │
                           │  source attribution   │    └──────────────────────────┘
                           └──────────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
- **Tool:** Claude Code
- **Input:** The Chunking Strategy section from this planning.md (chunk size 400 chars / 200 char overlap, recursive boundary-aware splitting, document type rationale)
- **Expected output:** A `chunk_and_embed.py` with a `recursive_split()` function that splits on `\n## `, `\n### `, `\n\n`, `\n`, `. ` in that order before falling back to raw character splits, plus an `add_overlap()` function
- **Verification:** Run the script, inspect the printed chunk counts per file, spot-check 5 random chunks to confirm no chunk contains text from two unrelated sections and no chunk exceeds ~1,800 characters

**Milestone 4 — Embedding and retrieval:**
- **Tool:** Claude Code
- **Input:** The Retrieval Approach section (model: `all-MiniLM-L6-v2`, top-k: 5, ChromaDB persistent store) and the Architecture diagram showing the ChromaDB stage
- **Expected output:** The `chunk_and_embed.py` ChromaDB section — `collection.add()` with `ids`, `embeddings`, `documents`, and `metadatas` (source URL, filename, chunk_index); and the `answer_question()` function in `app.py` that queries by embedding vector and returns top-5 results with metadata
- **Verification:** After running `chunk_and_embed.py`, open a Python REPL and query the collection manually with a known term (e.g., "hash table") and confirm the top result comes from `coding_interview_university.txt`

**Milestone 5 — Generation and interface:**
- **Tool:** Claude Code
- **Input:** The grounding rule from this planning.md ("answer using ONLY information found in context"), the Evaluation Plan's 5 test questions, and the Architecture diagram's Generation stage
- **Expected output:** `app.py` Gradio UI with a question text box, answer output box, and a retrieved-sources panel; system prompt that cites filenames inline and ends with a Sources section; temperature set to 0.2 to reduce hallucination risk
- **Verification:** Run all 5 test questions from the Evaluation Plan; confirm each answer contains at least one `[filename]` inline citation and ends with a populated Sources section; confirm the model says "My sources don't cover this" when asked an off-topic question (e.g., "What is the capital of France?")
