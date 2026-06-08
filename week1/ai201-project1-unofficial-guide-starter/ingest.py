#!/usr/bin/env python3
"""
Document Ingestion Pipeline — Tech Job Interview Tips Unofficial Guide

Fetches 10 documents from two source types:
  - GitHub (3 documents): README files from well-known interview prep repos
  - Reddit (7 documents): top self-posts from r/cscareerquestions and r/leetcode
    via Reddit's public JSON API (no API key required)

Each document is cleaned and saved as a .txt file in documents/.
Running this script is all you need to populate the documents/ directory
before chunking and embedding.

Usage:
    python ingest.py
"""

import re
import time
from pathlib import Path

import requests

# ── Config ─────────────────────────────────────────────────────────────────────

DOCUMENTS_DIR = Path("documents")

# Reddit requires a descriptive User-Agent to avoid 429s
HEADERS = {
    "User-Agent": "ai201-interview-guide-research/1.0 (educational RAG project)"
}

# Seconds to wait between requests — keeps us well under Reddit's rate limit
REQUEST_DELAY = 1.5

# ── Source definitions ──────────────────────────────────────────────────────────

GITHUB_SOURCES = [
    {
        "name": "coding_interview_university",
        "owner": "jwasham",
        "repo": "coding-interview-university",
        "branch": "main",
        "path": "README.md",
        "description": "Self-taught study plan for getting a SWE job at a top company",
    },
    {
        "name": "system_design_primer",
        "owner": "donnemartin",
        "repo": "system-design-primer",
        "branch": "master",
        "path": "README.md",
        "description": "Community guide to system design interviews",
    },
    {
        "name": "tech_interview_handbook",
        "owner": "yangshun",
        "repo": "tech-interview-handbook",
        "branch": "main",
        "path": "README.md",
        "description": "Curated interview materials: algorithms, behavioral, negotiation",
    },
]

REDDIT_SOURCES = [
    {"subreddit": "cscareerquestions", "limit": 5},
    {"subreddit": "leetcode", "limit": 2},
]


# ── Cleaners ───────────────────────────────────────────────────────────────────

def clean_github_markdown(text: str) -> str:
    """
    Remove elements that add noise without semantic value:
      - Badge links:  [![alt](img)](href)  and  ![alt](img)
      - HTML comments and inline HTML tags
      - Markdown table separator rows (---|---|---)
      - Excessive blank lines (3+ → 2)
    """
    # Badge-style links that wrap an image
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
    # Standalone markdown images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # HTML block comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Inline HTML tags (e.g. <br>, <details>, <summary>)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Markdown table alignment rows
    text = re.sub(r'^\|[-| :]+\|$', '', text, flags=re.MULTILINE)
    # Collapse 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def clean_reddit_text(text: str) -> str:
    """
    Normalize Reddit post text and comments:
      - Decode common HTML entities
      - Replace bare URLs with [link] so prose stays readable
      - Collapse blank lines
    Returns empty string if the text was deleted or removed.
    """
    if not text or text in ('[deleted]', '[removed]'):
        return ''
    text = (
        text
        .replace('&amp;', '&')
        .replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&nbsp;', ' ')
        .replace('&#x200B;', '')   # zero-width space Reddit adds
    )
    # Strip bare URLs (keep the surrounding sentence intact)
    text = re.sub(r'https?://\S+', '[link]', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── Fetchers ───────────────────────────────────────────────────────────────────

def get(url: str, **params) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp


def fetch_github_file(owner: str, repo: str, branch: str, path: str) -> str:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    return get(url).text


def fetch_reddit_top_posts(subreddit: str, limit: int) -> list[dict]:
    """Return up to `limit` self-posts with meaningful text content."""
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    # Over-fetch so we can filter out link posts and near-empty posts
    data = get(url, t="all", limit=limit * 4).json()
    posts = []
    for child in data["data"]["children"]:
        post = child["data"]
        if post.get("is_self") and len(post.get("selftext", "")) > 200:
            posts.append(post)
        if len(posts) >= limit:
            break
    return posts


def fetch_top_comments(permalink: str, max_comments: int = 8) -> list[str]:
    """Return cleaned top-scored comments from a Reddit thread."""
    url = f"https://www.reddit.com{permalink}.json"
    data = get(url, limit=30, sort="top").json()
    comments = []
    for child in data[1]["data"]["children"]:
        if child["kind"] != "t1":
            continue
        body = clean_reddit_text(child["data"].get("body", ""))
        score = child["data"].get("score", 0)
        if body and score >= 10 and len(body) > 60:
            comments.append(f"[upvotes: {score}]\n{body}")
        if len(comments) >= max_comments:
            break
    return comments


# ── Writers ────────────────────────────────────────────────────────────────────

def save_document(filename: str, content: str, source_url: str) -> None:
    path = DOCUMENTS_DIR / filename
    header = f"Source: {source_url}\n{'=' * 60}\n\n"
    path.write_text(header + content, encoding="utf-8")
    word_count = len(content.split())
    print(f"  + {filename}  ({word_count:,} words)")


# ── Pipeline stages ────────────────────────────────────────────────────────────

def ingest_github() -> None:
    print("\n[Stage 1/2]  GitHub READMEs")
    for src in GITHUB_SOURCES:
        try:
            print(f"  Fetching {src['owner']}/{src['repo']} ...")
            raw = fetch_github_file(src["owner"], src["repo"], src["branch"], src["path"])
            cleaned = clean_github_markdown(raw)

            # Very large READMEs (system-design-primer is ~80 k chars) would
            # create unmanageable chunks. Cap at ~6 k words of content.
            MAX_CHARS = 35_000
            if len(cleaned) > MAX_CHARS:
                cleaned = cleaned[:MAX_CHARS] + "\n\n[content truncated for length]"

            repo_url = f"https://github.com/{src['owner']}/{src['repo']}"
            save_document(f"{src['name']}.txt", cleaned, repo_url)
            time.sleep(REQUEST_DELAY)
        except Exception as exc:
            print(f"  ERROR  {src['name']}: {exc}")


def ingest_reddit() -> None:
    print("\n[Stage 2/2]  Reddit posts")
    doc_index = 1
    for src in REDDIT_SOURCES:
        subreddit = src["subreddit"]
        print(f"  Fetching top posts from r/{subreddit} ...")
        try:
            posts = fetch_reddit_top_posts(subreddit, src["limit"])
            for post in posts:
                title = post["title"]
                body = clean_reddit_text(post.get("selftext", ""))
                permalink = post.get("permalink", "")

                comments: list[str] = []
                if permalink:
                    try:
                        comments = fetch_top_comments(permalink)
                        time.sleep(REQUEST_DELAY)
                    except Exception:
                        pass  # comments are a nice-to-have; don't abort on failure

                content = f"# {title}\n\n{body}"
                if comments:
                    content += "\n\n## Top Comments\n\n" + "\n\n---\n\n".join(comments)

                filename = f"reddit_{subreddit}_{doc_index:02d}.txt"
                post_url = f"https://reddit.com{permalink}"
                save_document(filename, content, post_url)
                doc_index += 1
                time.sleep(REQUEST_DELAY)
        except Exception as exc:
            print(f"  ERROR  r/{subreddit}: {exc}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    DOCUMENTS_DIR.mkdir(exist_ok=True)
    print("=== Tech Interview Tips — Document Ingestion Pipeline ===")
    print(f"Output: {DOCUMENTS_DIR.resolve()}")

    ingest_github()
    ingest_reddit()

    docs = sorted(DOCUMENTS_DIR.glob("*.txt"))
    total_words = sum(len(p.read_text(encoding="utf-8").split()) for p in docs)
    print(f"\n=== Done: {len(docs)} documents, {total_words:,} total words ===")
    for p in docs:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
