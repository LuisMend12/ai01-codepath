#!/usr/bin/env python3
"""Temporary debug: print the exact context + prompt sent to Groq and the raw response."""
import os
import re
import textwrap
from pathlib import Path

import chromadb
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
RETRIEVAL_POOL = 15
RRF_K = 60

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


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


model = SentenceTransformer(EMBEDDING_MODEL)
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_collection(COLLECTION_NAME)
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

store = collection.get(include=["documents", "metadatas"])
chunk_lookup = {doc_id: {"text": t, "meta": m} for doc_id, t, m in zip(store["ids"], store["documents"], store["metadatas"])}
bm25_ids = store["ids"]
bm25_index = BM25Okapi([_tokenize(t) for t in store["documents"]])

query = "What data structures should I study first for coding interviews?"

query_vec = model.encode([query])[0].tolist()
results = collection.query(query_embeddings=[query_vec], n_results=RETRIEVAL_POOL, include=[])
semantic_ids = results["ids"][0]

scores = bm25_index.get_scores(_tokenize(query))
order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
bm25_ranked = [bm25_ids[i] for i in order[:RETRIEVAL_POOL]]

fused_scores = {}
for ranking in [semantic_ids, bm25_ranked]:
    for rank, doc_id in enumerate(ranking):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:TOP_K]

context_parts = []
for i, doc_id in enumerate(ranked_ids, 1):
    meta = chunk_lookup[doc_id]["meta"]
    text = chunk_lookup[doc_id]["text"]
    context_parts.append(f"[Passage {i}]\nFile: {meta['filename']}\nSource URL: {meta['source']}\n\n{text}")
context = "\n\n---\n\n".join(context_parts)

print("=== RETRIEVED CONTEXT ===")
print(context)
print("\n=== END CONTEXT ===\n")

user_message = f"Context:\n\n{context}\n\nQuestion: {query}"
response = groq_client.chat.completions.create(
    model=GROQ_MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ],
    temperature=0.2,
    max_tokens=900,
)
print("=== GROQ RESPONSE ===")
print(response.choices[0].message.content)
print("\n=== FINISH REASON ===")
print(response.choices[0].finish_reason)
