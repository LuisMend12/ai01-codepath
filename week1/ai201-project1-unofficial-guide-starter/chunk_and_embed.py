#!/usr/bin/env python3
"""
Chunking and Embedding Pipeline

Reads every .txt file from documents/, splits each one into overlapping
chunks using a recursive boundary-aware splitter, embeds all chunks with
sentence-transformers, and persists everything to a local ChromaDB collection.

Run once after ingest.py:
    python chunk_and_embed.py

Re-running is safe — the collection is dropped and rebuilt from scratch.
"""

import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

DOCUMENTS_DIR = Path("documents")
CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "interview_tips"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ~400 tokens at ~4 chars/token; fits one coherent idea from a guide section
# or 1–3 Reddit paragraphs without blending unrelated advice.
MAX_CHARS = 1_600
# ~50 tokens — carries setup sentences across paragraph-boundary splits,
# a common pattern in Reddit posts (setup paragraph → punchline paragraph).
OVERLAP_CHARS = 200


# ── Document parsing ────────────────────────────────────────────────────────────

def parse_document(text: str) -> tuple[str, str]:
    """
    Return (source_url, body) from a file written by ingest.py.
    The file format is:
        Source: <url>
        ============================================================

        <body text>
    """
    source_url = ""
    body_lines = []
    past_separator = False

    for line in text.splitlines():
        if not past_separator:
            if line.startswith("Source: "):
                source_url = line[len("Source: "):].strip()
            elif line.startswith("=" * 10):
                past_separator = True
        else:
            body_lines.append(line)

    return source_url, "\n".join(body_lines).strip()


# ── Chunking ────────────────────────────────────────────────────────────────────

# Ordered from coarsest to finest structural boundary.
_SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". "]


def _recursive_split(text: str, sep_idx: int, max_chars: int) -> list[str]:
    if len(text) <= max_chars or sep_idx >= len(_SEPARATORS):
        stripped = text.strip()
        return [stripped] if stripped else []

    sep = _SEPARATORS[sep_idx]
    parts = re.split(re.escape(sep), text)
    chunks: list[str] = []
    current = ""

    for part in parts:
        joined = (current + sep + part) if current else part
        if len(joined) <= max_chars:
            current = joined
        else:
            if current:
                chunks.append(current.strip())
            if len(part) > max_chars:
                sub = _recursive_split(part, sep_idx + 1, max_chars)
                if sub:
                    chunks.extend(sub[:-1])
                    current = sub[-1]
                else:
                    current = ""
            else:
                current = part

    if current and current.strip():
        chunks.append(current.strip())

    return chunks


def _add_overlap(chunks: list[str], overlap_chars: int) -> list[str]:
    if len(chunks) <= 1:
        return chunks
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prefix = chunks[i - 1][-overlap_chars:].strip()
        result.append(prefix + " " + chunks[i] if prefix else chunks[i])
    return result


def chunk_document(filename: str, source_url: str, body: str) -> list[dict]:
    raw = _recursive_split(body, sep_idx=0, max_chars=MAX_CHARS)
    with_overlap = _add_overlap(raw, OVERLAP_CHARS)
    return [
        {
            "text": chunk,
            "source": source_url,
            "filename": filename,
            "chunk_index": idx,
        }
        for idx, chunk in enumerate(with_overlap)
        if chunk.strip()
    ]


# ── Main pipeline ───────────────────────────────────────────────────────────────

def main() -> None:
    if not DOCUMENTS_DIR.exists() or not any(DOCUMENTS_DIR.glob("*.txt")):
        print(
            "ERROR: No documents found in documents/\n"
            "Run `python ingest.py` first to populate the documents/ folder."
        )
        return

    CHROMA_DIR.mkdir(exist_ok=True)

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Dropped existing collection (rebuilding from scratch).")
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    all_chunks: list[dict] = []
    for doc_path in sorted(DOCUMENTS_DIR.glob("*.txt")):
        text = doc_path.read_text(encoding="utf-8")
        source_url, body = parse_document(text)
        chunks = chunk_document(doc_path.name, source_url, body)
        all_chunks.extend(chunks)
        print(f"  {doc_path.name:<45} {len(chunks):>4} chunks")

    print(f"\nTotal chunks across all documents: {len(all_chunks)}")
    print("Embedding and storing in ChromaDB...")

    texts = [c["text"] for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    collection.add(
        ids=[f"chunk_{i}" for i in range(len(all_chunks))],
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[
            {
                "source": c["source"],
                "filename": c["filename"],
                "chunk_index": c["chunk_index"],
            }
            for c in all_chunks
        ],
    )

    print(f"\nDone. {len(all_chunks)} chunks stored in {CHROMA_DIR}/")
    print("Run `python app.py` to start the query interface.")


if __name__ == "__main__":
    main()
