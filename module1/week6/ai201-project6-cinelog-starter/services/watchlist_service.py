from models import db, Film, WatchlistEntry, User


def add_to_watchlist(user_id, film_id):
    """Add a film to a user's watchlist.

    Raises ValueError for unknown user or film IDs.
    """
    user = User.query.get(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    film = Film.query.get(film_id)
    if film is None:
        raise ValueError(f"Film {film_id!r} not found")

    existing = WatchlistEntry.query.filter_by(user_id=user_id, film_id=film_id).first()
    if existing:
        return existing

    entry = WatchlistEntry(user_id=user_id, film_id=film_id)
    db.session.add(entry)
    db.session.commit()
    return entry


def get_watchlist(user_id):
    """Return a user's public watchlist."""
    user = User.query.get(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    entries = (
        WatchlistEntry.query
        .join(Film)
        .filter(WatchlistEntry.user_id == user_id)
        .order_by(WatchlistEntry.added_at.desc())
        .all()
    )
    return [_entry_dict(e) for e in entries]


def _entry_dict(entry):
    return {
        "film_id": entry.film_id,
        "title": entry.film.title,
        "year": entry.film.year,
        "director": entry.film.director,
        "public": entry.public,
        "added_at": entry.added_at.isoformat(),
    }
