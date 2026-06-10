#!/usr/bin/env python3
"""Temporary debug script: print 5 random chunks from the ChromaDB collection."""
import random

import chromadb

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "interview_tips"

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_collection(COLLECTION_NAME)

store = collection.get(include=["documents", "metadatas"])
ids = store["ids"]
docs = store["documents"]
metas = store["metadatas"]

print(f"Total chunks: {len(ids)}\n")

random.seed(7)
sample_indices = random.sample(range(len(ids)), 5)

with open("sample_chunks.txt", "w", encoding="utf-8") as f:
    for idx in sample_indices:
        meta = metas[idx]
        text = docs[idx]
        header = (
            f"=== Chunk {idx} | id={ids[idx]} | file={meta['filename']} "
            f"| chunk_index={meta['chunk_index']} | len={len(text)} chars ==="
        )
        f.write(header + "\n")
        f.write(text + "\n\n")

print("Wrote sample_chunks.txt")
