"""Seed the Mixtape database with realistic test data.

Run: python seed_data.py
"""

from datetime import datetime, timedelta, date
from app import create_app
from models import db, User, Song, Listen, Friendship, Playlist, PlaylistSong, Notification

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    # ── Users ────────────────────────────────────────────────────────────────
    kenji  = User(username="kenji",  streak=12, last_listen_date=date.today() - timedelta(days=1))
    nova   = User(username="nova",   streak=5,  last_listen_date=date.today())
    darius = User(username="darius", streak=3,  last_listen_date=date.today() - timedelta(days=1))
    simone = User(username="simone", streak=7,  last_listen_date=date.today())
    aaliya = User(username="aaliya", streak=9,  last_listen_date=date.today())
    db.session.add_all([kenji, nova, darius, simone, aaliya])
    db.session.commit()

    # ── Songs ────────────────────────────────────────────────────────────────
    songs_data = [
        ("Crown Heights Anthem", "Borough Kings",  aaliya.id),
        ("Neon City",            "The Synthwave",   kenji.id),
        ("Midnight Run",         "Borough Kings",   darius.id),
        ("Electric Feel",        "MGMT",            nova.id),
        ("Golden Hour",          "JVKE",            simone.id),
        ("Anthem of the World",  "Global Chorus",   kenji.id),
        ("Friday Energy",        "Weekend Vibes",   simone.id),
        ("Moonrise",             "Luna Park",       aaliya.id),
    ]
    songs = [Song(title=t, artist=a, shared_by=u) for t, a, u in songs_data]
    db.session.add_all(songs)
    db.session.commit()
    crown, neon, midnight, electric, golden, anthem_world, friday_e, moonrise = songs

    # ── Friendships (bidirectional) ──────────────────────────────────────────
    pairs = [
        (nova.id, darius.id), (darius.id, nova.id),
        (nova.id, kenji.id),  (kenji.id, nova.id),
        (aaliya.id, kenji.id),(kenji.id, aaliya.id),
        (simone.id, darius.id),(darius.id, simone.id),
    ]
    db.session.add_all([Friendship(user_id=u, friend_id=f) for u, f in pairs])
    db.session.commit()

    # ── Playlists ────────────────────────────────────────────────────────────
    friday = Playlist(name="Friday Energy", created_by=darius.id)
    vibes  = Playlist(name="Morning Vibes", created_by=nova.id)
    anthems = Playlist(name="Anthems",      created_by=simone.id)
    db.session.add_all([friday, vibes, anthems])
    db.session.commit()

    # Friday Energy: 7 songs (positions 1–7) — reproduces Bug #5 (last song hidden)
    friday_songs = [neon, electric, golden, midnight, crown, anthem_world, friday_e]
    for i, s in enumerate(friday_songs, start=1):
        db.session.add(PlaylistSong(playlist_id=friday.id, song_id=s.id, position=i,
                                    added_at=datetime.utcnow() - timedelta(hours=7 - i)))

    # Morning Vibes: 3 songs
    for i, s in enumerate([golden, electric, moonrise], start=1):
        db.session.add(PlaylistSong(playlist_id=vibes.id, song_id=s.id, position=i,
                                    added_at=datetime.utcnow() - timedelta(hours=3 - i)))

    # Anthems: crown appears here too (and in friday) → Bug #3 returns it 2x
    # Add crown to a third playlist to make it appear 3x when searching "Anthem"
    anthems2 = Playlist(name="Hype Anthems", created_by=kenji.id)
    db.session.add(anthems2)
    db.session.commit()

    for i, s in enumerate([crown, anthem_world], start=1):
        db.session.add(PlaylistSong(playlist_id=anthems.id, song_id=s.id, position=i,
                                    added_at=datetime.utcnow()))
    for i, s in enumerate([crown, moonrise], start=1):
        db.session.add(PlaylistSong(playlist_id=anthems2.id, song_id=s.id, position=i,
                                    added_at=datetime.utcnow()))
    db.session.commit()

    # ── Listen history ────────────────────────────────────────────────────────
    # Bug #2: darius listened at 11 PM yesterday — should NOT appear in "now" feed
    # but the 24-hour rolling window keeps him visible until 11 PM today.
    yesterday_11pm = datetime.utcnow().replace(hour=23, minute=0, second=0) - timedelta(days=1)
    db.session.add(Listen(user_id=darius.id, song_id=neon.id, timestamp=yesterday_11pm))

    # nova listened 30 minutes ago — definitely "now"
    db.session.add(Listen(user_id=nova.id, song_id=electric.id,
                           timestamp=datetime.utcnow() - timedelta(minutes=30)))

    # kenji has a legitimate streak listen (yesterday)
    db.session.add(Listen(user_id=kenji.id, song_id=crown.id,
                           timestamp=datetime.utcnow() - timedelta(days=1)))

    db.session.commit()

    # ── Existing notification (playlist-add works) ────────────────────────────
    db.session.add(Notification(
        user_id=aaliya.id,
        message='kenji added your song "Crown Heights Anthem" to the playlist "Friday Energy".',
        created_at=datetime.utcnow() - timedelta(hours=2),
    ))
    db.session.commit()

    print("OK Seed data loaded.")
    print(f"  Users: {', '.join(u.username for u in [kenji, nova, darius, simone, aaliya])}")
    print(f"  Songs: {len(songs)}")
    print(f"  Playlists: friday({friday.id}), vibes({vibes.id}), anthems({anthems.id}), hype({anthems2.id})")
    print(f"  friday Energy has {PlaylistSong.query.filter_by(playlist_id=friday.id).count()} songs")
    print()
    print("Key IDs for testing:")
    print(f"  kenji={kenji.id}  nova={nova.id}  darius={darius.id}  simone={simone.id}  aaliya={aaliya.id}")
    print(f"  crown={crown.id}  neon={neon.id}  friday_playlist={friday.id}")
