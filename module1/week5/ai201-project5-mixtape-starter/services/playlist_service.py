"""Playlist service — CRUD and song membership."""

from datetime import datetime
from models import db, Playlist, PlaylistSong, Song, User
from services import notification_service


def get_playlist(playlist_id):
    pl = Playlist.query.get_or_404(playlist_id)
    return {"id": pl.id, "name": pl.name, "created_by": pl.created_by}


def get_playlist_songs(playlist_id):
    """Return all songs in a playlist ordered by position.

    BUG #5: The query filters by `position < total` (strict less-than) instead
    of `position <= total`.  Positions are 1-based, so a playlist with N songs
    has positions 1…N and `position < N` excludes the song at position N (the
    most recently added one).  When a new song is added (N becomes N+1) the
    previous last song at position N is now < N+1 so it appears, but the new
    song at position N+1 is filtered out.  The symptom is exactly "the last
    song is always missing; adding another frees the previous one."
    """
    Playlist.query.get_or_404(playlist_id)
    total = PlaylistSong.query.filter_by(playlist_id=playlist_id).count()

    # ── BUG #5 ──────────────────────────────────────────────────────────────
    rows = (
        db.session.query(PlaylistSong)
        .filter_by(playlist_id=playlist_id)
        .filter(PlaylistSong.position <= total)
        .order_by(PlaylistSong.position)
        .all()
    )
    # ────────────────────────────────────────────────────────────────────────

    return [
        {
            "position": r.position,
            "song_id": r.song_id,
            "title": r.song.title,
            "artist": r.song.artist,
            "added_at": r.added_at.isoformat(),
        }
        for r in rows
    ]


def add_song_to_playlist(playlist_id, song_id, added_by_user_id):
    """Add a song to a playlist and notify the song's sharer."""
    pl = Playlist.query.get_or_404(playlist_id)
    Song.query.get_or_404(song_id)

    next_pos = (PlaylistSong.query.filter_by(playlist_id=playlist_id).count() or 0) + 1
    entry = PlaylistSong(
        playlist_id=playlist_id,
        song_id=song_id,
        position=next_pos,
        added_at=datetime.utcnow(),
    )
    db.session.add(entry)
    db.session.commit()

    notification_service.notify_song_added_to_playlist(song_id, pl.name, added_by_user_id)
    return {"added": True, "position": next_pos}


def create_playlist(name, created_by):
    pl = Playlist(name=name, created_by=created_by)
    db.session.add(pl)
    db.session.commit()
    return {"id": pl.id, "name": pl.name}
