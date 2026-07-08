"""Feed service — Friends Listening Now and activity feed."""

from datetime import datetime, timedelta, date
from models import db, User, Listen, Friendship, Song


def get_friends_listening_now(user_id):
    """Return friends who have a recent listen.

    BUG #2: Uses a rolling 24-hour window (datetime.utcnow() - timedelta(hours=24))
    instead of a calendar-day boundary (midnight of today).  At 9 AM on Monday the
    cutoff is 9 AM on Sunday, so a friend who listened at 11 PM Sunday evening is
    still included even though they haven't listened "today."  The window should
    start at midnight of the current calendar day.
    """
    friend_rows = Friendship.query.filter_by(user_id=user_id).all()
    friend_ids = [r.friend_id for r in friend_rows]

    today = date.today()
    cutoff = datetime(today.year, today.month, today.day)  # midnight of today (UTC)

    results = []
    for fid in friend_ids:
        friend = User.query.get(fid)
        latest = (
            Listen.query
            .filter_by(user_id=fid)
            .filter(Listen.timestamp >= cutoff)
            .order_by(Listen.timestamp.desc())
            .first()
        )
        if latest:
            results.append({
                "user_id": fid,
                "username": friend.username,
                "song_id": latest.song_id,
                "song_title": latest.song.title,
                "artist": latest.song.artist,
                "listened_at": latest.timestamp.isoformat(),
            })
    return results
