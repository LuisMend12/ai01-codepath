"""
Collect raw Hacker News posts via the Algolia HN Search API (no auth, no
rate limits) and write them to data/raw_posts.csv.

Pulls three pools, each tied to a real, community-recognized HN posting
convention:
  - "ask_hn":  posts tagged ask_hn (the "Ask HN:" submission flow)
  - "show_hn": posts tagged show_hn (the "Show HN:" submission flow)
  - "story":   posts tagged story but NOT ask_hn/show_hn (ordinary link
               submissions of third-party content)

This script does NOT assign final labels or build the model-input text —
it only collects raw data. Run label_dataset.py afterward.
"""
import csv
import os
import time

import requests

BASE = "https://hn.algolia.com/api/v1/search_by_date"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw_posts.csv")

HITS_PER_PAGE = 100
PAGES_PER_TAG = 3  # 300 raw hits per tag before filtering


def fetch_tag(tag, pages=PAGES_PER_TAG):
    hits = []
    for page in range(pages):
        resp = requests.get(
            BASE,
            params={"tags": tag, "hitsPerPage": HITS_PER_PAGE, "page": page},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        page_hits = data.get("hits", [])
        if not page_hits:
            break
        hits.extend(page_hits)
        time.sleep(0.2)
    return hits


def main():
    rows = []
    seen_ids = set()

    for tag, label_source in [("ask_hn", "ask_hn"), ("show_hn", "show_hn"), ("story", "story")]:
        print(f"Fetching tag={tag}...")
        hits = fetch_tag(tag)
        kept = 0
        for hit in hits:
            object_id = hit.get("objectID")
            if object_id in seen_ids:
                continue
            tags = hit.get("_tags", [])

            # For the "story" pool, exclude anything that's actually ask_hn/show_hn
            # so the three pools stay mutually exclusive.
            if tag == "story" and ("ask_hn" in tags or "show_hn" in tags):
                continue

            title = hit.get("title")
            if not title:
                continue

            seen_ids.add(object_id)
            kept += 1
            rows.append(
                {
                    "id": object_id,
                    "label_source": label_source,
                    "title": title,
                    "story_text": hit.get("story_text") or "",
                    "url": hit.get("url") or "",
                    "points": hit.get("points") or 0,
                    "num_comments": hit.get("num_comments") or 0,
                    "created_at": hit.get("created_at") or "",
                    "author": hit.get("author") or "",
                    "permalink": f"https://news.ycombinator.com/item?id={object_id}",
                }
            )
        print(f"  kept {kept} unique '{label_source}' posts (raw hits: {len(hits)})")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id", "label_source", "title", "story_text", "url", "points",
                "num_comments", "created_at", "author", "permalink",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} unique posts to {OUT_PATH}")
    counts = {}
    for r in rows:
        counts[r["label_source"]] = counts.get(r["label_source"], 0) + 1
    print("Label source distribution:")
    for k, v in counts.items():
        print(f"  {k:<10} {v}")


if __name__ == "__main__":
    main()
