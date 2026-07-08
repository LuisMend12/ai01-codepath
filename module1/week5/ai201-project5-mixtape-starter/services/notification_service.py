"""Notification service — creates in-app notifications."""

from models import db, Notification, Song, User


def notify_song_added_to_playlist(song_id, playlist_name, added_by_user_id):
    """Notify the song's original sharer that someone added it to a playlist."""
    song = Song.query.get(song_id)
    if not song or not song.shared_by:
        return
    adder = User.query.get(added_by_user_id)
    if not adder:
        return
    # Don't notify when you add your own song.
    if song.shared_by == added_by_user_id:
        return

    note = Notification(
        user_id=song.shared_by,
        message=(
            f"{adder.username} added your song \"{song.title}\" "
            f"to the playlist \"{playlist_name}\"."
        ),
    )
    db.session.add(note)
    db.session.commit()


def notify_song_rated(song_id, rated_by_user_id, rating):
    """Notify the song's original sharer that someone rated it."""
    song = Song.query.get(song_id)
    if not song or not song.shared_by:
        return
    rater = User.query.get(rated_by_user_id)
    if not rater:
        return
    if song.shared_by == rated_by_user_id:
        return

    note = Notification(
        user_id=song.shared_by,
        message=(
            f"{rater.username} rated your song \"{song.title}\" "
            f"{rating} star{'s' if rating != 1 else ''}."
        ),
    )
    db.session.add(note)
    db.session.commit()
