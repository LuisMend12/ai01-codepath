from models import db, Film, Collection, User


def add_to_collection(user_id, film_id):
    """Add a film to a user's watched collection.

    Returns the existing Collection entry if the film is already present,
    or creates and returns a new one.
    Raises ValueError for unknown user or film IDs.
    """
    user = User.query.get(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    film = Film.query.get(film_id)
    if film is None:
        raise ValueError(f"Film {film_id!r} not found")

    existing = Collection.query.filter_by(user_id=user_id, film_id=film_id).first()
    if existing:
        return existing

    entry = Collection(user_id=user_id, film_id=film_id)
    db.session.add(entry)
    db.session.commit()
    return entry


def get_collection(user_id):
    """Return a user's collection sorted alphabetically by film title."""
    user = User.query.get(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    entries = (
        Collection.query
        .join(Film)
        .filter(Collection.user_id == user_id)
        .order_by(Film.title)
        .all()
    )
    return [_entry_dict(e) for e in entries]


def _entry_dict(entry):
    return {
        "film_id": entry.film_id,
        "title": entry.film.title,
        "year": entry.film.year,
        "director": entry.film.director,
        "added_at": entry.added_at.isoformat(),
    }
