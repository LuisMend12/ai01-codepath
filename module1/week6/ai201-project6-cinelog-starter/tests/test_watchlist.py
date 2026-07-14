import pytest
from app import create_app
from models import db as _db, User, Film, WatchlistEntry


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
    with app.app_context():
        user = User(username="bob", email="bob@example.com")
        film = Film(title="Parasite", year=2019, director="Bong Joon-ho")
        _db.session.add_all([user, film])
        _db.session.commit()
        yield {"user_id": user.id, "film_id": film.id}


def test_add_to_watchlist_nonexistent_film_raises(seeded, app):
    from services.watchlist_service import add_to_watchlist
    with app.app_context():
        with pytest.raises(ValueError, match="not found"):
            add_to_watchlist(seeded["user_id"], "00000000-0000-0000-0000-000000000000")
