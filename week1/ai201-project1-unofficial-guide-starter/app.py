#!/usr/bin/env python3
"""
Query Interface — Tech Interview Unofficial Guide

Gradio web app that:
  1. Embeds the user's question with the same model used at index time
  2. Retrieves relevant chunks from ChromaDB (semantic similarity) and/or a
     BM25 keyword index (lexical match), fusing the two with Reciprocal Rank
     Fusion when "Hybrid" mode is selected
  3. Sends those chunks to Groq under a strict grounding prompt
  4. Returns a grounded answer with inline citations and a Sources section

Setup (run once):
    cp .env.example .env          # add your GROQ_API_KEY
    python ingest.py              # fetch documents
    python chunk_and_embed.py     # build the vector index

Then start the UI:
    python app.py
"""

import os
import re
import textwrap
from pathlib import Path

import chromadb
import gradio as gr
from dotenv import load_dotenv
from groq import Groq
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "interview_tips"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5
# Each retriever returns this many candidates before fusion narrows to TOP_K.
RETRIEVAL_POOL = 15
# Standard RRF damping constant — large enough that being rank 1 vs. rank 2
# in one retriever doesn't completely dominate the fused score.
RRF_K = 60

SEMANTIC_ONLY = "Semantic only"
HYBRID = "Hybrid (Semantic + BM25)"

# ── Grounding prompt ────────────────────────────────────────────────────────────
# Explicit rules prevent the model from reaching into its training data.
# The citation instruction ([filename]) gives every claim a traceable source.

SYSTEM_PROMPT = textwrap.dedent("""\
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
""")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# ── Load models, vector store, and BM25 index once at startup ───────────────────

def _load_resources():
    if not CHROMA_DIR.exists():
        raise RuntimeError(
            "chroma_db/ not found. Run `python chunk_and_embed.py` first."
        )
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

    print("Building BM25 keyword index from stored chunks...")
    store = collection.get(include=["documents", "metadatas"])
    chunk_lookup = {
        doc_id: {"text": text, "meta": meta}
        for doc_id, text, meta in zip(store["ids"], store["documents"], store["metadatas"])
    }
    bm25_ids = store["ids"]
    bm25_index = BM25Okapi([_tokenize(t) for t in store["documents"]])

    print(f"Vector store loaded — {collection.count()} chunks ready (semantic + BM25).")
    return model, collection, groq_client, chunk_lookup, bm25_ids, bm25_index


_embed_model, _collection, _groq, _chunk_lookup, _bm25_ids, _bm25_index = _load_resources()


# ── Retrieval ───────────────────────────────────────────────────────────────────

def _semantic_ranking(query: str) -> list[str]:
    """Return chunk ids ranked by cosine similarity, most similar first."""
    query_vec = _embed_model.encode([query])[0].tolist()
    pool = min(RETRIEVAL_POOL, len(_bm25_ids))
    results = _collection.query(query_embeddings=[query_vec], n_results=pool, include=[])
    return results["ids"][0]


def _bm25_ranking(query: str) -> list[str]:
    """Return chunk ids ranked by BM25 score, highest first."""
    scores = _bm25_index.get_scores(_tokenize(query))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [_bm25_ids[i] for i in order[:RETRIEVAL_POOL]]


def _rrf_fuse(rankings: list[list[str]], k: int = RRF_K) -> list[str]:
    """Combine multiple ranked id lists via Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def _retrieve(query: str, mode: str) -> list[dict]:
    """Return up to TOP_K chunks, each tagged with which retriever(s) found it."""
    semantic_ids = _semantic_ranking(query)

    if mode == SEMANTIC_ONLY:
        ranked_ids = semantic_ids[:TOP_K]
        methods = {doc_id: {"semantic"} for doc_id in ranked_ids}
    else:
        bm25_ids_ranked = _bm25_ranking(query)
        ranked_ids = _rrf_fuse([semantic_ids, bm25_ids_ranked])[:TOP_K]
        sem_set = set(semantic_ids)
        bm25_set = set(bm25_ids_ranked)
        methods = {}
        for doc_id in ranked_ids:
            tags = set()
            if doc_id in sem_set:
                tags.add("semantic")
            if doc_id in bm25_set:
                tags.add("keyword")
            methods[doc_id] = tags

    return [
        {
            "id": doc_id,
            "text": _chunk_lookup[doc_id]["text"],
            "meta": _chunk_lookup[doc_id]["meta"],
            "methods": methods[doc_id],
        }
        for doc_id in ranked_ids
    ]


# ── Core retrieval + generation ─────────────────────────────────────────────────

def answer_question(query: str, mode: str) -> tuple[str, str]:
    """
    Returns (answer, retrieved_sources_markdown).
    Splitting the outputs lets Gradio display them in separate boxes.
    """
    query = query.strip()
    if not query:
        return "Please enter a question.", ""

    chunks = _retrieve(query, mode)

    # Build numbered context block for the prompt
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["meta"]
        context_parts.append(
            f"[Passage {i}]\n"
            f"File: {meta['filename']}\n"
            f"Source URL: {meta['source']}\n\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Call Groq with the grounding prompt
    user_message = f"Context:\n\n{context}\n\nQuestion: {query}"
    response = _groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    answer = response.choices[0].message.content

    # Build a readable sources panel, tagging which retriever(s) found each source
    seen = set()
    source_lines = []
    for chunk in chunks:
        meta = chunk["meta"]
        key = meta["filename"]
        if key not in seen:
            seen.add(key)
            tags = "+".join(sorted(chunk["methods"])) if mode == HYBRID else "semantic"
            source_lines.append(f"**{meta['filename']}** _(matched via: {tags})_\n{meta['source']}")
    sources_md = "\n\n".join(source_lines)

    return answer, sources_md


# ── Gradio UI ───────────────────────────────────────────────────────────────────

EXAMPLE_QUESTIONS = [
    "What data structures should I study first for coding interviews?",
    "How do I negotiate a job offer at a tech company?",
    "What system design topics come up most in FAANG interviews?",
    "How many LeetCode problems should I solve before interviewing?",
    "What behavioral interview questions come up most often at top companies?",
]

with gr.Blocks(title="Tech Interview Unofficial Guide", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# Tech Interview Unofficial Guide\n"
        "Answers grounded in community knowledge from GitHub guides and "
        "r/cscareerquestions · r/leetcode. Every claim is cited."
    )

    with gr.Row():
        with gr.Column(scale=3):
            query_box = gr.Textbox(
                label="Your question",
                placeholder="e.g. What LeetCode patterns come up most in FAANG interviews?",
                lines=3,
            )
            mode_radio = gr.Radio(
                choices=[HYBRID, SEMANTIC_ONLY],
                value=HYBRID,
                label="Retrieval mode",
                info="Hybrid combines semantic similarity with BM25 keyword matching via Reciprocal Rank Fusion.",
            )
            submit_btn = gr.Button("Ask", variant="primary")
            gr.Examples(
                examples=EXAMPLE_QUESTIONS,
                inputs=query_box,
                label="Example questions",
            )
        with gr.Column(scale=4):
            answer_box = gr.Textbox(
                label="Answer (with source citations)",
                lines=16,
                interactive=False,
            )
            sources_box = gr.Markdown(label="Retrieved sources")

    submit_btn.click(
        fn=answer_question,
        inputs=[query_box, mode_radio],
        outputs=[answer_box, sources_box],
    )
    query_box.submit(
        fn=answer_question,
        inputs=[query_box, mode_radio],
        outputs=[answer_box, sources_box],
    )

if __name__ == "__main__":
    demo.launch()
