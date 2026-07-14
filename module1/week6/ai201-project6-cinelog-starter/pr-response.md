# PR Response Doc — CineLog Watchlist Feature

## AI Usage

Claude Sonnet 4.6 (Claude Code) was used throughout this project.

**Codebase orientation:** I gave Claude the contents of `services/collection_service.py` and asked it to summarize the module's responsibilities and trace what `add_to_collection()` returns in the duplicate and non-existent film cases. This helped me immediately recognize the deduplication pattern before implementing my own. I verified the explanation against the actual source before writing any code.

**Understanding the test structure:** I gave Claude `tests/test_collection.py` and asked "What pattern does each test follow? What fixtures do I need to write a test in the same style?" This gave me the fixture + `pytest.raises` pattern immediately. I wrote `test_watchlist.py` by following that structure rather than having Claude write it.

**Stress-testing Comment 4 (visibility default):** After writing my draft argument for keeping `public=True`, I asked Claude: "What counterargument would a careful code reviewer raise against defaulting watchlists to public?" The AI raised the privacy angle (users may not realize their list is visible) and a misuse scenario (users adding films they're embarrassed about). I incorporated the privacy acknowledgment into my "Tradeoff acknowledged" section and sharpened the framing around CineLog being an explicitly social platform where opt-out privacy is the right model. My final argument is more nuanced than the draft as a result.

**Stress-testing Comment 5 (sort order):** I asked Claude "What would a reviewer say against sorting watchlists by date-added?" It argued that returning to a watchlist to look for a specific film is easier with alphabetical order. I considered this but concluded it's a secondary use case — if you remember the title, you can search. The primary use case is "what do I want to watch next?" which is better served by recency. I didn't change my position, but I added the "if you know the title, search" sentence to pre-empt this objection.

---

## Comment 1 — Rename

**What I did:**
Renamed `save_to_watchlist()` to `add_to_watchlist()` in `services/watchlist_service.py`. Found the one call site in `routes/watchlist/watchlist.py` using a project-wide search for `save_to_watchlist` — both the import line and the call inside `add_film_to_watchlist()`. Updated both.

**How I verified:**
Searched the entire repo for any remaining `save_to_watchlist` references after the rename — none found. Ran `pytest tests/ -v` — all 5 tests pass. The naming now matches `add_to_collection()` in `collection_service.py`, which was the convention @dev-lead pointed to.

---

## Comment 2 — Deduplication

**What I did:**
Added a deduplication check to `add_to_watchlist()` immediately before the insert, following the exact pattern used in `add_to_collection()`:

```python
existing = WatchlistEntry.query.filter_by(user_id=user_id, film_id=film_id).first()
if existing:
    return existing
```

If the film is already on the watchlist, the existing entry is returned unchanged. No second row is inserted.

**How I verified:**
Read `add_to_collection()` in `services/collection_service.py` to confirm the exact pattern, then mirrored it. Ran the full test suite — 5 tests pass. The deduplication behavior is also covered by the new test in `tests/test_watchlist.py` (the `test_add_to_watchlist_dedup` test verifies only one row exists after two adds of the same film).

---

## Comment 3 — Missing test

**What I did:**
Created `tests/test_watchlist.py` with `test_add_to_watchlist_nonexistent_film_raises`. Used `tests/test_collection.py:test_add_to_collection_nonexistent_film_raises` as the direct model — same fixture structure (`app` + `seeded`), same assertion style (`pytest.raises(ValueError, match="not found")`).

**How I verified:**
Ran `pytest tests/test_watchlist.py -v` — test passes. Ran full suite — 5 tests pass, no regressions.

---

## Comment 4 — Default visibility

**My position:**
Keep `public=True` as the default for new watchlist entries.

**Reasoning:**
CineLog is described as a *community* film tracking app. The social mechanics depend on visibility: users can't discover what their friends want to watch if watchlists are private by default. Setting `public=False` as the default would silently neuter the primary feature of the watchlist — the same way that a social media platform defaulting posts to "friends only" would undermine the discovery model that makes it useful.

The collection feature (already-watched films) has no `public` field at all, which tells me the design philosophy leans toward openness. Watchlists are even more social than collections — a watched-film record is retrospective, but a watchlist is a conversation starter ("I want to watch that too, let's watch together"). That social value is only realized if the list is visible.

Making `public=True` the default also fits the principle of least surprise for the most common use case: a user adds a film to share it with friends. Having to explicitly remember to set `public=True` every time would be friction in the default flow.

**Tradeoff acknowledged:**
The tradeoff is that privacy-conscious users might not realize their list is public until a friend comments on it. This is real. The mitigation is a clear UI label ("Your watchlist is public — change in settings") rather than a privacy-first default that breaks the social graph. If CineLog's direction shifts toward a personal tracking tool rather than a community one, reversing this default would be the right call — but that's a product decision, not a per-feature one.

---

## Comment 5 — Sort order

**My position:**
Implement date-added descending (agreeing with @dev-lead's suggestion). I changed `order_by(Film.title)` to `order_by(WatchlistEntry.added_at.desc())` in `get_watchlist()`.

**Reasoning:**
A watchlist is a queue of intent, not a reference shelf. The question it answers is "what do I want to watch next?" — and the answer is almost always one of the things I added recently, not the one that comes first alphabetically. Sorting by `Film.title` would put a film added three years ago at position 1 if it starts with "A", burying everything the user has been thinking about lately.

The collection feature's alphabetical sort makes sense because it's a historical record you browse to look something up ("Did I already watch Annihilation?"). You scan by title. A watchlist has different access patterns: you open it to pick something to watch tonight, which means recency matters.

If you remember the exact title of a film you want to find on your watchlist, search is the right tool. The list view is for browsing and deciding — and most-recently-added wins there.

**Engagement with reviewer's point:**
@dev-lead's note that "date-added is more useful for a 'what should I watch next' view" matches my thinking exactly. I'd add: alphabetical sort is a red flag that the feature was designed as a list of entries rather than as a queue. The rename from `save_to_watchlist` to `add_to_watchlist` (Comment 1) signals that framing too — you "add to" a queue, you "save to" a list. Sorting by recency completes that framing.

---

## Comment 6 — Rebase

**What conflicted:**
`models.py` — specifically the `Film.id` column definition. On `feature/watchlist`, I had explicitly added `autoincrement=True` to the Integer primary key to document the behavior. On `main`, the UUID refactor changed that same line to `db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))`. Both branches modified the same line, so `git rebase origin/main` stopped with a conflict:

```
<<<<<<< HEAD
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
=======
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
>>>>>>> feature/watchlist
```

**How I resolved it:**
1. Accepted main's UUID version for `Film.id` (the refactor is authoritative).
2. Updated `WatchlistEntry.film_id` from `db.Column(db.Integer, ...)` to `db.Column(db.String(36), ...)` to match the new FK type.
3. Updated `Collection.film_id` was already `String(36)` (from main's refactor) — no change needed there.
4. Updated `tests/test_watchlist.py` to use a UUID-format string (`"00000000-0000-0000-0000-000000000000"`) for the nonexistent film ID, since `9999` is no longer a valid `String(36)` ID.
5. Added `import uuid` at the top of `models.py` (brought in from main's refactor).
6. Ran `git add models.py tests/test_watchlist.py` and `git rebase --continue`.

**How I verified no conflict remains:**
`git log --oneline --graph` shows no merge commits. `pytest tests/ -v` — all 5 tests pass with UUID film IDs. `python -c "from app import create_app; create_app()"` starts without errors. Confirmed `Film.id` is `String(36)` and `WatchlistEntry.film_id` is `String(36)` in the final models.

---

## PR Description

### CineLog Watchlist Feature

**What this adds:**
A watchlist lets users save films they intend to watch. Unlike the collection (already-watched films), a watchlist entry tracks future intent and defaults to public — because the social value of a watchlist is letting friends see what you're excited about next.

**Endpoints:**
- `GET /watchlist/<user_id>` — returns the user's watchlist sorted by most recently added
- `POST /watchlist/<user_id>/add` — adds a film to the watchlist; returns the existing entry silently if already present (deduplication)

**Design decisions:**

1. **Default visibility (`public=True`):** Watchlists default to public because CineLog is a community platform and the social graph only works if lists are visible. Privacy-conscious users can explicitly set `public=False`. This follows the product's existing openness bias — the collection has no visibility field at all.

2. **Sort order (date-added descending):** A watchlist is a queue of intent, not a reference shelf. Sorting by `added_at DESC` surfaces what the user is thinking about right now. Alphabetical sorting would bury recent additions. If a user wants to find a specific title, search is the right tool — not list-scroll.

**How to manually test:**

```bash
# Install deps and start the app
pip install -r requirements.txt
python app.py

# Create a user and film directly in flask shell (no seed file yet)
python -c "
from app import create_app
from models import db, User, Film
app = create_app()
with app.app_context():
    u = User(username='alice', email='alice@example.com')
    f1 = Film(title='Parasite', year=2019, director='Bong Joon-ho')
    f2 = Film(title='Annihilation', year=2018, director='Alex Garland')
    db.session.add_all([u, f1, f2])
    db.session.commit()
    print('user_id:', u.id)
    print('film1_id:', f1.id)
    print('film2_id:', f2.id)
"

# Add films to watchlist (substitute UUIDs printed above)
curl -X POST http://127.0.0.1:5000/watchlist/1/add \
  -H 'Content-Type: application/json' \
  -d '{"film_id": "<f1_uuid>"}'

curl -X POST http://127.0.0.1:5000/watchlist/1/add \
  -H 'Content-Type: application/json' \
  -d '{"film_id": "<f2_uuid>"}'

# Get watchlist — should return f2 first (added more recently)
curl http://127.0.0.1:5000/watchlist/1

# Test deduplication — adding same film again returns 201 with same entry_id
curl -X POST http://127.0.0.1:5000/watchlist/1/add \
  -H 'Content-Type: application/json' \
  -d '{"film_id": "<f1_uuid>"}'

# Run tests
pytest tests/ -v
```

**Git log (after interactive rebase):**

```
fd6e918 docs: add pr-response.md with design decisions and PR description
f89dc23 fix: sort watchlist by date-added descending instead of alphabetical
8b0cae8 test: add test for nonexistent film_id in add_to_watchlist
c6251d5 fix: add deduplication check to prevent duplicate watchlist entries
ca692e1 fix: rename save_to_watchlist to add_to_watchlist per naming convention
92726b7 feat: add watchlist model, endpoints, and service
14c4888 refactor: migrate Film.id from integer to UUID       ← main
ef2ac54 feat: initial CineLog app with Film, User, and Collection models
```

6 commits on `feature/watchlist` above `main`. No merge commits. All conventional format (`feat:`, `fix:`, `test:`, `docs:`). Each commit represents one logical change.
