import pytest
from app import create_app
from models import db as _db, User, Film, Collection


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
        user = User(username="alice", email="alice@example.com")
        film = Film(title="Mulholland Drive", year=2001, director="David Lynch")
        _db.session.add_all([user, film])
        _db.session.commit()
        yield {"user_id": user.id, "film_id": film.id}


def test_add_to_collection(seeded, app):
    from services.collection_service import add_to_collection
    with app.app_context():
        entry = add_to_collection(seeded["user_id"], seeded["film_id"])
        assert entry.user_id == seeded["user_id"]
        assert entry.film_id == seeded["film_id"]


def test_add_to_collection_dedup(seeded, app):
    from services.collection_service import add_to_collection
    with app.app_context():
        e1 = add_to_collection(seeded["user_id"], seeded["film_id"])
        e2 = add_to_collection(seeded["user_id"], seeded["film_id"])
        assert e1.id == e2.id
        assert (
            Collection.query
            .filter_by(user_id=seeded["user_id"], film_id=seeded["film_id"])
            .count()
        ) == 1


def test_add_to_collection_nonexistent_film_raises(seeded, app):
    from services.collection_service import add_to_collection
    with app.app_context():
        with pytest.raises(ValueError, match="not found"):
            add_to_collection(seeded["user_id"], 9999)


def test_get_collection_sorted_alphabetically(seeded, app):
    from services.collection_service import add_to_collection, get_collection
    with app.app_context():
        film2 = Film(title="Annihilation", year=2018, director="Alex Garland")
        _db.session.add(film2)
        _db.session.commit()

        add_to_collection(seeded["user_id"], seeded["film_id"])
        add_to_collection(seeded["user_id"], film2.id)

        result = get_collection(seeded["user_id"])
        titles = [r["title"] for r in result]
        assert titles == sorted(titles)
