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

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

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

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
