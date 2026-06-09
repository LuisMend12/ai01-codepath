#!/usr/bin/env python3
"""
Query Interface — Tech Interview Unofficial Guide

Gradio web app that:
  1. Embeds the user's question with the same model used at index time
  2. Retrieves the top-5 semantically closest chunks from ChromaDB
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
import textwrap
from pathlib import Path

import chromadb
import gradio as gr
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "interview_tips"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5

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


# ── Load models and vector store once at startup ────────────────────────────────

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
    print(f"Vector store loaded — {collection.count()} chunks ready.")
    return model, collection, groq_client


_embed_model, _collection, _groq = _load_resources()


# ── Core retrieval + generation ─────────────────────────────────────────────────

def answer_question(query: str) -> tuple[str, str]:
    """
    Returns (answer, retrieved_sources_markdown).
    Splitting the outputs lets Gradio display them in separate boxes.
    """
    query = query.strip()
    if not query:
        return "Please enter a question.", ""

    # 1. Embed query and retrieve top-k chunks
    query_vec = _embed_model.encode([query])[0].tolist()
    results = _collection.query(
        query_embeddings=[query_vec],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    # 2. Build numbered context block for the prompt
    context_parts = []
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        context_parts.append(
            f"[Passage {i}]\n"
            f"File: {meta['filename']}\n"
            f"Source URL: {meta['source']}\n\n"
            f"{doc}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # 3. Call Groq with the grounding prompt
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

    # 4. Build a readable sources panel for the UI
    seen = set()
    source_lines = []
    for meta, dist in zip(metas, distances):
        key = meta["filename"]
        if key not in seen:
            seen.add(key)
            similarity = 1 - dist  # cosine distance → similarity
            source_lines.append(
                f"**{meta['filename']}** (similarity: {similarity:.2f})\n{meta['source']}"
            )
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
        inputs=query_box,
        outputs=[answer_box, sources_box],
    )
    query_box.submit(
        fn=answer_question,
        inputs=query_box,
        outputs=[answer_box, sources_box],
    )

if __name__ == "__main__":
    demo.launch()
