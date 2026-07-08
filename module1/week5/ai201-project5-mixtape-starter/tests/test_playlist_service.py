"""Regression tests for playlist_service.

Bug #5 regression: get_playlist_songs() must return ALL songs in a playlist,
including the last one.  The original code used `position < total` (strict
less-than) which always excluded the song at position N.  These tests would
have caught that before it shipped.
"""

import pytest
from datetime import datetime
from app import create_app
from models import db as _db, User, Song, Playlist, PlaylistSong


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture
def seeded(app):
    """A playlist with 3 songs at positions 1, 2, 3 and a user to own them."""
    with app.app_context():
        user = User(username="testuser", streak=0)
        _db.session.add(user)
        _db.session.flush()

        songs = [
            Song(title=f"Song {i}", artist="Artist", shared_by=user.id)
            for i in range(1, 4)
        ]
        _db.session.add_all(songs)
        _db.session.flush()

        playlist = Playlist(name="Test Playlist", created_by=user.id)
        _db.session.add(playlist)
        _db.session.flush()

        for pos, song in enumerate(songs, start=1):
            _db.session.add(
                PlaylistSong(
                    playlist_id=playlist.id,
                    song_id=song.id,
                    position=pos,
                    added_at=datetime.utcnow(),
                )
            )
        _db.session.commit()
        yield {"playlist_id": playlist.id, "song_ids": [s.id for s in songs]}


def test_all_songs_returned(seeded, app):
    """get_playlist_songs() must return every song, including position N."""
    from services.playlist_service import get_playlist_songs

    with app.app_context():
        result = get_playlist_songs(seeded["playlist_id"])

    assert len(result) == 3, (
        f"Expected 3 songs but got {len(result)}. "
        "Bug #5: position < total excludes the last song."
    )
    positions = [r["position"] for r in result]
    assert positions == [1, 2, 3], f"Expected positions [1,2,3], got {positions}"


def test_last_song_is_included(seeded, app):
    """The song at position == total must be present in the result."""
    from services.playlist_service import get_playlist_songs

    with app.app_context():
        result = get_playlist_songs(seeded["playlist_id"])

    max_position = max(r["position"] for r in result)
    assert max_position == 3, (
        f"Highest returned position is {max_position}; expected 3. "
        "Bug #5: the last song is always missing."
    )


def test_adding_a_song_shows_all_songs(seeded, app):
    """After adding a 4th song, all 4 must appear — not 3 with the new one hidden."""
    from services.playlist_service import get_playlist_songs, add_song_to_playlist

    with app.app_context():
        # Add a 4th song
        extra = Song(title="Song 4", artist="Artist", shared_by=1)
        _db.session.add(extra)
        _db.session.flush()
        add_song_to_playlist(seeded["playlist_id"], extra.id, added_by_user_id=1)

        result = get_playlist_songs(seeded["playlist_id"])

    assert len(result) == 4, (
        f"Expected 4 songs after adding one, got {len(result)}. "
        "Bug #5: adding a song 'freed' position N but hid position N+1."
    )
    positions = sorted(r["position"] for r in result)
    assert positions == [1, 2, 3, 4]
