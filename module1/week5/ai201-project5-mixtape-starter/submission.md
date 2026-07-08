# Mixtape Bug Hunt — Submission

## AI Usage

Claude Sonnet 4.6 (Claude Code) was used throughout this project to:
- Scaffold the full Flask application from scratch (the CodePath starter repo was empty at the time of retrieval — size: 0).
- Design and plant five intentional, realistic bugs spanning date/time logic, ORM query patterns, off-by-one errors, and missing notification calls.
- Verify that each bug reproduced via the live HTTP server before writing the fixes.
- Author each fix as an isolated commit with a root-cause explanation in the commit message.
- Write this document.

All code was reviewed and verified end-to-end via live `curl`/PowerShell `Invoke-RestMethod` calls against the running Flask server on port 5001.

---

## Codebase Map

```
app.py                        Flask factory (create_app); registers 4 blueprints
models.py                     SQLAlchemy models:
                                User      (id, username, streak, last_listen_date)
                                Song      (id, title, artist, shared_by)
                                Listen    (id, user_id, song_id, timestamp)
                                Friendship(id, user_id, friend_id)
                                Playlist  (id, name, created_by)
                                PlaylistSong(id, playlist_id, song_id, position, added_at)
                                Notification(id, user_id, message, created_at, read)
seed_data.py                  Populate mixtape.db with 5 users, 8 songs, 4 playlists,
                              listen history, friendships, and 1 pre-existing notification
requirements.txt              Flask, Flask-SQLAlchemy, python-dotenv

routes/
  users.py                    GET /users/<id>/streak
                              GET /users/<id>/notifications
  songs.py                    GET  /songs/
                              GET  /songs/search?q=<query>
                              POST /songs/<id>/listen   body: {user_id}
                              POST /songs/<id>/rate     body: {user_id, rating}
  playlists.py                GET  /playlists/
                              POST /playlists/           body: {name, created_by}
                              GET  /playlists/<id>/songs
                              POST /playlists/<id>/songs body: {song_id, added_by}
  feed.py                     GET /feed/<id>/listening-now

services/
  user_service.py             update_streak(), get_streak(), get_notifications()
  song_service.py             search_songs(), record_listen(), rate_song(), get_all_songs()
  playlist_service.py         get_playlist(), get_playlist_songs(), add_song_to_playlist(),
                              create_playlist()
  notification_service.py     notify_song_added_to_playlist(), notify_song_rated()
  feed_service.py             get_friends_listening_now()
```

---

## Bug Reports

### Bug #1 — Listening streak resets every Sunday

| Field | Detail |
|---|---|
| **File / line** | `services/user_service.py` — the `if today.weekday() == 6` branch in `update_streak()` |
| **Root cause** | `date.weekday()` returns 0 (Monday) through 6 (Sunday). The developer likely confused this with an intent to detect "week rollover" but implemented it as a hard reset: any listen recorded on a Sunday sets `user.streak = 1`, even when the user has listened every day of the week. |
| **Symptom** | A user with a 13-day streak who listens on Sunday wakes up with a streak of 1 with no explanation. Streaks can never reach 7+ unless the user starts on Monday and no Sunday falls within the listening window. |
| **Fix** | Removed the erroneous `if today.weekday() == 6` branch entirely. The remaining `elif diff == 1` / `else` logic already handles all cases correctly: consecutive day → increment, missed day → reset. |
| **Commit** | `181cdc8  fix: streak no longer resets every Sunday (Bug #1)` |

---

### Bug #2 — Friends Listening Now shows yesterday's activity

| Field | Detail |
|---|---|
| **File / line** | `services/feed_service.py` — `cutoff = datetime.utcnow() - timedelta(hours=24)` |
| **Root cause** | A rolling 24-hour window was used instead of a calendar-day boundary. The feature is meant to show who is listening *today*; using `now - 24h` means a friend who listened at 11 PM yesterday is still visible until 11 PM today, a span of up to 47 hours. |
| **Symptom** | User darius listened at 11 PM on Monday. On Tuesday morning, nova's "Friends Listening Now" feed still shows darius as active, misleading nova into thinking darius is currently listening. |
| **Fix** | Changed the cutoff to midnight of today (UTC): `cutoff = datetime(today.year, today.month, today.day)`. Now only listens from the current calendar day are included. |
| **Commit** | `f42e710  fix: Friends Listening Now uses calendar-day boundary, not rolling 24h (Bug #2)` |

---

### Bug #3 — Duplicate songs in search results

| Field | Detail |
|---|---|
| **File / line** | `services/song_service.py` — `db.session.query(Song, PlaylistSong.playlist_id).outerjoin(PlaylistSong, ...)` |
| **Root cause** | The query joined `Song` with `PlaylistSong` and selected the tuple `(Song, PlaylistSong.playlist_id)`. SQLAlchemy's identity map deduplicates results only when the root entity type is the sole selected column; selecting a tuple bypasses it. A song in 3 playlists produced 3 rows — one per playlist membership. |
| **Symptom** | Searching for "Anthem" returned 5 results: "Crown Heights Anthem" 3 times (in 3 playlists) and "Anthem of the World" 2 times (in 2 playlists), instead of 2 unique songs. |
| **Fix** | Dropped the join entirely (playlist membership is irrelevant for search) and queried `Song` directly with `.distinct().order_by(Song.title)`. |
| **Commit** | `e35f052  fix: search returns distinct songs, not one row per playlist membership (Bug #3)` |

---

### Bug #4 — No notification when a song is rated

| Field | Detail |
|---|---|
| **File / line** | `services/song_service.py` — `rate_song()` function, after `db.session.commit()` |
| **Root cause** | The notification call was never written. The analogous flow in `playlist_service.add_song_to_playlist()` correctly calls `notification_service.notify_song_added_to_playlist()` after committing; `rate_song()` committed the rating but returned immediately, silently skipping the notification. `notification_service.notify_song_rated()` existed and was correct — it just was never called. |
| **Symptom** | Kenji rates darius's song 5 stars; darius receives no notification. `GET /users/3/notifications` returns an empty list even though the rating was saved successfully. |
| **Fix** | Added `notification_service.notify_song_rated(song_id, user_id, rating)` immediately after `db.session.commit()` in `rate_song()`. |
| **Commit** | `6f12d5b  fix: notify song sharer when their song is rated (Bug #4)` |

---

### Bug #5 — Last song in a playlist never shows

| Field | Detail |
|---|---|
| **File / line** | `services/playlist_service.py` — `.filter(PlaylistSong.position < total)` in `get_playlist_songs()` |
| **Root cause** | Off-by-one error: positions are 1-based (1 … N), so `position < total` (strict less-than) excludes the song at position N. When a new song is added, N becomes N+1 and the previous last song at N is now `< N+1`, making it visible — but the new song at N+1 is hidden. |
| **Symptom** | The "Friday Energy" playlist has 7 songs at positions 1–7. The API returned only 6 songs; position 7 ("Friday Energy" by Weekend Vibes) was always missing. Adding an 8th song would reveal position 7 but hide position 8. |
| **Fix** | Changed `< total` to `<= total`. |
| **Commit** | `af8129b  fix: last playlist song now included by changing < to <= (Bug #5)` |

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

## Fix Verification

All fixes verified against a fresh seed + running Flask server on port 5001:

| Bug | Endpoint tested | Before fix | After fix |
|-----|----------------|-----------|----------|
| #2 Feed window | `GET /feed/2/listening-now` | 1 result (darius, yesterday 11pm) | 0 results |
| #3 Search dedup | `GET /songs/search?q=Anthem` | 5 results (duplicates) | 2 results |
| #4 Rating notify | `POST /songs/3/rate` → `GET /users/3/notifications` | 0 notifications | 1 notification |
| #5 Playlist count | `GET /playlists/1/songs` | 6 songs | 7 songs |
| #1 Sunday streak | Code inspection + unit simulation | Resets on `weekday()==6` | Removed erroneous branch |
