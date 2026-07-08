"""Song service — search, listen recording, and rating."""

from datetime import datetime
from models import db, Song, Listen, PlaylistSong, User
from services import notification_service


def search_songs(query):
    """Search songs by title or artist.

    BUG #3: The query joins Song with PlaylistSong and selects the pair
    (Song, PlaylistSong.playlist_id) rather than Song alone.  SQLAlchemy's
    identity map only deduplicates when the root entity is the sole column
    selection; selecting a tuple bypasses that deduplication.  A song that
    appears in 3 playlists therefore appears 3 times in the result list.
    The fix is to drop the join (playlist membership is irrelevant for search)
    and query Song directly with .distinct().
    """
    songs = (
        Song.query
        .filter(
            db.or_(
                Song.title.ilike(f"%{query}%"),
                Song.artist.ilike(f"%{query}%"),
            )
        )
        .distinct()
        .order_by(Song.title)
        .all()
    )
    return [_song_dict(song) for song in songs]


def record_listen(user_id, song_id):
    """Record a song play and update the user's streak."""
    from services.user_service import update_streak
    Song.query.get_or_404(song_id)
    listen = Listen(user_id=user_id, song_id=song_id, timestamp=datetime.utcnow())
    db.session.add(listen)
    db.session.commit()
    streak = update_streak(user_id)
    return {"recorded": True, "streak": streak}


def rate_song(user_id, song_id, rating):
    """Save a 1–5 star rating and notify the song's original sharer.

    BUG #4: The notification call is missing entirely.  The playlist-add flow
    (in playlist_service.add_song_to_playlist) correctly calls
    notification_service.notify_song_added_to_playlist() after saving.
    This function saves the rating but never calls
    notification_service.notify_song_rated(), so the sharer receives no
    notification.
    """
    song = Song.query.get_or_404(song_id)
    if not (1 <= rating <= 5):
        return {"error": "rating must be 1–5"}, 400

    # Persist the rating as a simple attribute on the song (avg for demo purposes).
    song.rating = rating
    db.session.commit()

    notification_service.notify_song_rated(song_id, user_id, rating)

    return {"rated": True, "song_id": song_id, "rating": rating}


def get_all_songs():
    return [_song_dict(s) for s in Song.query.order_by(Song.title).all()]


def _song_dict(song):
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "shared_by": song.shared_by,
    }
