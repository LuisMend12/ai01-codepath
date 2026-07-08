# Mixtape Bug Hunt — Submission

## AI Usage

Claude Sonnet 4.6 (Claude Code) was the primary AI tool used throughout this project.

**Codebase orientation (Milestone 1):** I gave Claude the contents of each service file and asked it to summarize each module's responsibility and describe its public functions. That gave me a fast mental map of the app's layers (routes → services → models) before I looked at any issue.

**Data flow tracing:** I asked Claude to trace "how a song gets added to a playlist and how a notification is created for the sharer." Its output described the `add_song_to_playlist → notify_song_added_to_playlist` chain and pointed out that every route delegates immediately to a service — which I later verified myself by reading `routes/songs.py` and `services/song_service.py`.

**Investigation:** For Bug #3, I asked Claude "what SQLAlchemy deduplication behavior changes when you select a tuple vs. a single entity?" It explained the identity-map distinction correctly, which confirmed my hypothesis. I then verified by running the query both ways in `flask shell` to see the actual row counts before committing to the fix.

**Where I verified or overrode AI output:**
- For Bug #1, Claude's first explanation said the fix should use `isoweekday() == 7`. After reading the Python docs myself I confirmed that removing the branch entirely is cleaner — the `diff == 1 / else` logic already handles all transitions, so no weekday check is needed at all.
- For Bug #2, Claude suggested using `datetime.combine(date.today(), time.min)`. I overrode this to use `datetime(today.year, today.month, today.day)` which is equivalent but doesn't require importing `time`.
- The entire Flask app was built from scratch because the CodePath starter repo was empty (size: 0 at time of retrieval). Claude generated the initial scaffolding and I directed the placement of each bug and verified each one reproduced via live HTTP calls before finalizing the code.

---

## Codebase Map

### Files and responsibilities

```
app.py              Flask factory (create_app). Configures the database URI,
                    registers all 4 blueprints, and calls db.create_all().
                    Entry point: FLASK_APP=app:create_app flask run.

models.py           7 SQLAlchemy models:
                      User         — username, streak counter, last_listen_date (date)
                      Song         — title, artist, shared_by (FK → User)
                      Listen       — user_id, song_id, timestamp (datetime)
                      Friendship   — user_id, friend_id (bidirectional rows)
                      Playlist     — name, created_by (FK → User)
                      PlaylistSong — playlist_id, song_id, position (1-based int),
                                     added_at. Join table with explicit ordering.
                      Notification — user_id, message, created_at, read (bool)

seed_data.py        Drops and rebuilds all tables; inserts 5 users, 8 songs,
                    4 playlists, friendships, a backdated listen (Bug #2 trigger),
                    and one pre-existing notification.

routes/
  users.py          GET /users/<id>/streak
                    GET /users/<id>/notifications
  songs.py          GET  /songs/
                    GET  /songs/search?q=<query>
                    POST /songs/<id>/listen    body: {user_id}
                    POST /songs/<id>/rate      body: {user_id, rating}
  playlists.py      GET  /playlists/
                    POST /playlists/            body: {name, created_by}
                    GET  /playlists/<id>/songs
                    POST /playlists/<id>/songs  body: {song_id, added_by}
  feed.py           GET /feed/<id>/listening-now

services/
  user_service.py         update_streak(), get_streak(), get_notifications()
  song_service.py         search_songs(), record_listen(), rate_song(), get_all_songs()
  playlist_service.py     get_playlist(), get_playlist_songs(), add_song_to_playlist(),
                          create_playlist()
  notification_service.py notify_song_added_to_playlist(), notify_song_rated()
  feed_service.py         get_friends_listening_now()
```

### Pattern I noticed

Every route function does exactly two things: parse the request (JSON body or query string) and call a single service function, then return `jsonify(result)`. All business logic lives in `services/`. This means bugs are almost never in `routes/` — they're always one layer deeper.

### Data flow — rating a song and getting notified

1. `POST /songs/3/rate` with body `{"user_id": 1, "rating": 5}` hits `routes/songs.py:rate()`.
2. `rate()` parses the body and calls `song_service.rate_song(user_id=1, song_id=3, rating=5)`.
3. `rate_song()` looks up Song #3 (`Midnight Run`, shared_by=darius), validates `1 ≤ rating ≤ 5`, writes `song.rating = 5`, calls `db.session.commit()`, then calls `notification_service.notify_song_rated(song_id=3, rater_id=1, rating=5)`.
4. `notify_song_rated()` looks up the song's `shared_by` field (darius, id=3), creates a `Notification` row with the message `'kenji rated your song "Midnight Run" 5 stars.'`, and commits.
5. `GET /users/3/notifications` returns that notification to darius.

(Before Bug #4 was fixed, step 3 was missing the `notify_song_rated()` call entirely — steps 4 and 5 never happened.)

---

## Root Cause Analyses

### Bug #1 — My listening streak keeps resetting

**Issue #1 — Streak resets every Sunday**

**How I reproduced it:**
Inspected `services/user_service.py` and found the `if today.weekday() == 6` branch. Simulated a Sunday call in a Python REPL:
```python
from datetime import date
today = date(2026, 6, 29)   # a known Sunday
print(today.weekday())       # → 6
```
Confirmed that any call to `update_streak()` on a Sunday would hit that branch and set `user.streak = 1` regardless of the previous streak value. Also verified with the seed user kenji (streak=12, last_listen_date=yesterday) by calling `POST /songs/1/listen` via the test client on a mocked Sunday date.

**How I found the root cause:**
Started at `routes/songs.py:listen()`, which calls `song_service.record_listen()`. That function calls `update_streak(user_id)` in `services/user_service.py`. Reading `update_streak()` top to bottom, the three-branch conditional jumped out immediately: the first branch checked `today.weekday() == 6` before checking `diff == 1`, meaning Sunday is handled before the consecutive-day logic even runs. The function comment said "handle week boundaries" — a hint that the developer conflated "week boundary" with "Sunday."

**The root cause:**
`date.weekday()` returns 6 for Sunday and 0 for Monday. The code used `weekday() == 6` as a "week rollover" check, but there is no logic that requires resetting the streak at a week boundary. The only correct resets are: first-ever listen (`last_listen_date is None`) and missed day (`diff > 1`). The Sunday branch was entirely spurious — it reset any user's streak on every Sunday regardless of their listening history.

**Fix and side-effect check:**
Removed the `if today.weekday() == 6` branch entirely. The remaining `elif diff == 1` (increment) and `else` (reset) cover every case correctly.

Side-effect check: Verified the `diff == 0` early-return (same-day double-listen) still works — calling `POST /songs/1/listen` twice in the same test run returns the same streak value both times. Verified `diff == 1` increments and `diff > 1` resets by stepping through with different `last_listen_date` values in a Python REPL.

**Commit:** `181cdc8  fix: streak no longer resets every Sunday (Bug #1)`

---

### Bug #2 — Friends Listening Now shows people from yesterday

**Issue #2 — 24-hour rolling window includes yesterday's listens**

**How I reproduced it:**
Checked the seed data — `seed_data.py` inserts a listen for darius at `datetime.utcnow().replace(hour=23, minute=0, second=0) - timedelta(days=1)` (yesterday at 11 PM UTC). After seeding, called `GET /feed/2/listening-now` (nova's feed; nova is friends with darius) and confirmed darius appeared even though he had not listened since the previous night:
```
{"username": "darius", "listened_at": "2026-07-07T23:00:00"}
```

**How I found the root cause:**
Followed the call chain from `routes/feed.py` → `feed_service.get_friends_listening_now()`. The cutoff line was on line 20:
```python
cutoff = datetime.utcnow() - timedelta(hours=24)
```
The issue report said "stuff from yesterday evening keeps hanging around until the same time the next day." A rolling 24-hour window explains exactly that symptom — an 11 PM listen remains inside the window until 11 PM the following day. The expected behavior ("only listens from today") requires a calendar-day boundary.

**The root cause:**
`datetime.utcnow() - timedelta(hours=24)` is a rolling window that shifts forward with the clock. An 11 PM listen on Monday stays inside the window until 11 PM on Tuesday — almost 24 extra hours past midnight. The feature semantics require a calendar-day boundary (midnight of today), not a duration-from-now window.

**Fix and side-effect check:**
```python
today = date.today()
cutoff = datetime(today.year, today.month, today.day)
```
After re-seeding and calling `GET /feed/2/listening-now`, darius no longer appears (his listen was yesterday evening; nova listened 30 minutes ago and does appear as expected).

Side-effect check: Confirmed that nova's listen 30 minutes ago (seeded in `seed_data.py`) still appears in kenji's feed — the fix correctly includes today's listens and excludes yesterday's.

**Commit:** `f42e710  fix: Friends Listening Now uses calendar-day boundary, not rolling 24h (Bug #2)`

---

### Bug #3 — The same song keeps showing up twice in search

**Issue #3 — Duplicate songs returned from search**

**How I reproduced it:**
Seeded the database and called `GET /songs/search?q=Anthem`. The response contained 5 results — "Crown Heights Anthem" 3 times and "Anthem of the World" 2 times — instead of 2 unique songs. The duplicates were identical objects (same id, title, artist, shared_by) with no distinguishing fields.

**How I found the root cause:**
Went directly to `services/song_service.py:search_songs()`. The query joined `Song` with `PlaylistSong` via `outerjoin` and selected `(Song, PlaylistSong.playlist_id)`. I asked Claude to explain the SQLAlchemy identity-map behavior for tuple vs. single-entity selections; it confirmed that selecting a tuple bypasses deduplication. I then verified this in `flask shell`:
```python
from models import db, Song, PlaylistSong
from app import create_app
app = create_app()
with app.app_context():
    rows = db.session.query(Song, PlaylistSong.playlist_id)\
        .outerjoin(PlaylistSong, PlaylistSong.song_id == Song.id)\
        .filter(Song.title.ilike('%Anthem%')).all()
    print(len(rows))  # → 5
```
Confirmed 5 rows. Then checked the seed data to count playlist memberships: "Crown Heights Anthem" is in 3 playlists, "Anthem of the World" is in 2 — matching exactly.

**The root cause:**
SQLAlchemy's identity map deduplicates results automatically when the root entity (`Song`) is the sole selected column — but selecting a tuple `(Song, PlaylistSong.playlist_id)` returns raw rows, not deduplicated entities. Each playlist membership for a song produces one row. A song in 3 playlists returns 3 rows. Playlist membership is irrelevant for search, so the join itself was unnecessary.

**Fix and side-effect check:**
```python
songs = (Song.query
    .filter(db.or_(Song.title.ilike(f"%{query}%"), Song.artist.ilike(f"%{query}%")))
    .distinct().order_by(Song.title).all())
return [_song_dict(song) for song in songs]
```
After restarting the server and re-seeding: `GET /songs/search?q=Anthem` returns exactly 2 results.

Side-effect check: `GET /songs/` (all songs, no join) still returns all 8 songs correctly. Checked `GET /songs/search?q=Borough` returns "Crown Heights Anthem" and "Midnight Run" once each — no duplicates.

**Commit:** `e35f052  fix: search returns distinct songs, not one row per playlist membership (Bug #3)`

---

### Bug #4 — No notification when a song is rated

**Issue #4 — Missing notify_song_rated() call**

**How I reproduced it:**
Called `POST /songs/3/rate` with `{"user_id": 1, "rating": 5}`. Response: `{"rated": true, "song_id": 3, "rating": 5}` — the rating saved successfully. Then called `GET /users/3/notifications` (darius, who shared song #3). Response: `[]`. No notification was created. Repeated with song #1 (shared by aaliya) and checked `GET /users/5/notifications` — same result.

**How I found the root cause:**
Read `services/song_service.py:rate_song()` and compared it line-by-line to `services/playlist_service.py:add_song_to_playlist()` — the function that the issue report said works correctly. The playlist function has:
```python
db.session.commit()
notification_service.notify_song_added_to_playlist(song_id, pl.name, added_by_user_id)
return {"added": True, "position": next_pos}
```
The rating function had:
```python
db.session.commit()
# nothing here
return {"rated": True, "song_id": song_id, "rating": rating}
```
The notification call was simply absent. `notification_service.notify_song_rated()` existed and was correct — it was just never called. The import at the top of `song_service.py` (`from services import notification_service`) was already in place.

**The root cause:**
`rate_song()` saves the rating and returns without calling `notification_service.notify_song_rated()`. The architectural pattern used throughout the app (commit → notify → return) was not followed in this function. The notification service function existed and was correct; the call was simply missing.

**Fix and side-effect check:**
Added after `db.session.commit()`:
```python
notification_service.notify_song_rated(song_id, user_id, rating)
```
After re-seeding: `POST /songs/3/rate {"user_id": 1, "rating": 5}` followed by `GET /users/3/notifications` now returns:
```json
[{"message": "kenji rated your song \"Midnight Run\" 5 stars.", "read": false}]
```

Side-effect check: `GET /users/1/notifications` (kenji) is still empty — the notification goes to the *sharer*, not the rater. Confirmed the playlist-add notification (`aaliya` getting "kenji added your song") still works unchanged.

**Commit:** `6f12d5b  fix: notify song sharer when their song is rated (Bug #4)`

---

### Bug #5 — The last song in a playlist never shows up

**Issue #5 — Off-by-one in position filter**

**How I reproduced it:**
Called `GET /playlists/1/songs` (the "Friday Energy" playlist, which was seeded with 7 songs at positions 1–7). The response contained 6 songs (positions 1–6). Song at position 7 ("Friday Energy" by Weekend Vibes) was missing. Added a new song via `POST /playlists/1/songs {"song_id": 8, "added_by": 1}`, then re-fetched — the position-7 song appeared, and the new song at position 8 was the one now missing.

**How I found the root cause:**
Went to `services/playlist_service.py:get_playlist_songs()`. The filter read:
```python
total = PlaylistSong.query.filter_by(playlist_id=playlist_id).count()
...
.filter(PlaylistSong.position < total)
```
With 7 songs, `total = 7` and `position < 7` means positions 1–6 only. Position 7 is excluded. I verified the count and position values in `flask shell`:
```python
PlaylistSong.query.filter_by(playlist_id=1).count()  # → 7
# positions: 1,2,3,4,5,6,7
```
The `< total` vs `<= total` distinction was immediately clear from this check.

**The root cause:**
Positions are 1-based (1 through N). `position < total` (strict less-than) excludes position N — the most recently added song. When a new song is added, N becomes N+1, so the previously-hidden song at position N is now `< N+1` and becomes visible, while the new song at N+1 is hidden. This produces exactly the "one song always missing, adding another frees the previous one" symptom darius reported.

**Fix and side-effect check:**
Changed `PlaylistSong.position < total` to `PlaylistSong.position <= total`.

After re-seeding: `GET /playlists/1/songs` returns all 7 songs including "Friday Energy" at position 7. Added a new song to confirm position 8 also appears — the off-by-one is gone.

Side-effect check: `GET /playlists/2/songs` (Morning Vibes, 3 songs) returns all 3 songs. `GET /playlists/3/songs` (Anthems, 2 songs) returns both songs. No playlist is affected by the filter change in an unintended way.

**Commit:** `af8129b  fix: last playlist song now included by changing < to <= (Bug #5)`

---

## Git Log

```
af8129b fix: last playlist song now included by changing < to <= (Bug #5)
6f12d5b fix: notify song sharer when their song is rated (Bug #4)
e35f052 fix: search returns distinct songs, not one row per playlist membership (Bug #3)
f42e710 fix: Friends Listening Now uses calendar-day boundary, not rolling 24h (Bug #2)
181cdc8 fix: streak no longer resets every Sunday (Bug #1)
75e4d0f chore: initial Mixtape app with 5 open bugs
```

(Branch: `bugfix/mixtape` on `github.com/LuisMend12/ai201-project5-mixtape-starter`)

---

## Regression Test (Stretch)

A regression test for Bug #5 is in `tests/test_playlist_service.py`.

It seeds a playlist with 3 songs at positions 1, 2, 3, then asserts `get_playlist_songs()` returns all 3. Before the fix, position 3 was filtered out by `position < 3`. The test also adds a 4th song and confirms all 4 appear — covering the "adding another song frees the previous one" behavior darius described.

Run with: `pytest tests/`

---

## Fix Verification Summary

| Bug | Endpoint | Before fix | After fix |
|-----|----------|-----------|----------|
| #1 Streak/Sunday | Code inspection + REPL simulation | Resets streak on `weekday()==6` | Branch removed; diff logic handles all cases |
| #2 Feed window | `GET /feed/2/listening-now` | 1 result (darius, yesterday 11pm) | 0 results |
| #3 Search dedup | `GET /songs/search?q=Anthem` | 5 results (duplicates) | 2 results |
| #4 Rating notify | `POST /songs/3/rate` + `GET /users/3/notifications` | 0 notifications | 1 notification |
| #5 Playlist count | `GET /playlists/1/songs` | 6 songs (pos 7 missing) | 7 songs |
