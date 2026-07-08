"""User service — streak tracking and profile helpers."""

from datetime import date
from models import db, User, Listen, Notification


def get_user(user_id):
    return User.query.get_or_404(user_id)


def update_streak(user_id):
    """Record a listen for today and update the user's consecutive-day streak.

    BUG #1: The branch `if today.weekday() == 6` treats Sunday (weekday 6) as
    a hard reset point regardless of whether the user actually listened
    consecutively.  The developer confused Python's weekday() (Mon=0…Sun=6)
    with the intent to detect a calendar-week boundary.  Any listen recorded on
    a Sunday resets the streak to 1 instead of continuing it.
    """
    user = User.query.get_or_404(user_id)
    today = date.today()

    if user.last_listen_date is None:
        user.streak = 1
        user.last_listen_date = today
        db.session.commit()
        return user.streak

    diff = (today - user.last_listen_date).days

    if diff == 0:
        # Already counted today — no change.
        return user.streak

    if diff == 1:
        user.streak += 1
    else:
        user.streak = 1

    user.last_listen_date = today
    db.session.commit()
    return user.streak


def get_streak(user_id):
    user = User.query.get_or_404(user_id)
    return {"user_id": user_id, "username": user.username, "streak": user.streak}


def get_notifications(user_id):
    User.query.get_or_404(user_id)
    notes = (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [
        {
            "id": n.id,
            "message": n.message,
            "created_at": n.created_at.isoformat(),
            "read": n.read,
        }
        for n in notes
    ]
