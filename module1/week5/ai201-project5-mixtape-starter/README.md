# Mixtape 🎵

A social music app where friends share songs, build collaborative playlists, and track listening stats.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
python seed_data.py                # seed the database

git checkout -b bugfix/mixtape

FLASK_APP=app:create_app flask run
```

> **Do not** use `python app.py` — that triggers a SQLAlchemy double-import error.
> Always start with `FLASK_APP=app:create_app flask run`.

App runs at `http://127.0.0.1:5000`.

## Project structure

```
app.py          — Flask factory (create_app)
models.py       — SQLAlchemy models: User, Song, Listen, Friendship,
                  Playlist, PlaylistSong, Notification
seed_data.py    — populates mixtape.db with test users/songs/playlists
routes/
  users.py      — GET /users/<id>/streak, GET /users/<id>/notifications
  songs.py      — GET /songs/, GET /songs/search, POST /songs/<id>/listen,
                  POST /songs/<id>/rate
  playlists.py  — GET|POST /playlists/, GET /playlists/<id>/songs,
                  POST /playlists/<id>/songs
  feed.py       — GET /feed/<id>/listening-now
services/
  user_service.py         — streak logic
  song_service.py         — search, listen recording, rating
  playlist_service.py     — playlist CRUD and song membership
  notification_service.py — in-app notification creation
  feed_service.py         — friends listening now
```

## Example call chain — sharing a song and getting notified

1. User A rates User B's song: `POST /songs/3/rate` with `{"user_id": 1, "rating": 5}`
2. `routes/songs.py:rate()` parses the request and calls `song_service.rate_song(1, 3, 5)`
3. `song_service.rate_song()` saves the rating, then (after the fix) calls
   `notification_service.notify_song_rated(3, 1, 5)`
4. `notify_song_rated` looks up the song's `shared_by` field, creates a `Notification`
   row for that user, and commits.
5. User B sees the notification at `GET /users/2/notifications`.

## Open issues

| # | Title | Affected service |
|---|---|---|
| 1 | Listening streak resets on Sundays | `services/user_service.py` |
| 2 | Friends Listening Now shows yesterday's activity | `services/feed_service.py` |
| 3 | Duplicate songs in search results | `services/song_service.py` |
| 4 | No notification when a song is rated | `services/song_service.py` + `notification_service.py` |
| 5 | Last song in a playlist never shows | `services/playlist_service.py` |
