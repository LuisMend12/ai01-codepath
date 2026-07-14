# CineLog

A community film tracking app where users build personal collections of watched films and maintain watchlists of films they intend to see.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
python app.py
```

App runs at `http://127.0.0.1:5000`. There is no frontend — the app exposes REST endpoints tested with `curl` or `pytest`.

## Project structure

```
app.py                         Flask factory (create_app); registers collection and watchlist blueprints
models.py                      SQLAlchemy models: User, Film, Collection, WatchlistEntry
routes/
  collection/collection.py     GET|POST /collection/<user_id> and /collection/<user_id>/add
  watchlist/watchlist.py       GET|POST /watchlist/<user_id> and /watchlist/<user_id>/add
services/
  collection_service.py        add_to_collection(), get_collection() — dedup + alphabetical sort
  watchlist_service.py         add_to_watchlist(), get_watchlist() — dedup + date-added sort
tests/
  test_collection.py           4 tests: add, dedup, nonexistent film, alphabetical sort
  test_watchlist.py            1 test: nonexistent film raises ValueError
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/collection/<user_id>` | List a user's watched films, sorted A–Z by title |
| POST | `/collection/<user_id>/add` | Add a film to a user's collection |
| GET | `/watchlist/<user_id>` | List a user's watchlist, newest-added first |
| POST | `/watchlist/<user_id>/add` | Add a film to a user's watchlist |

All `POST` endpoints expect `Content-Type: application/json` with a `film_id` field.

## Example usage

Seed some data in the Flask shell first:

```bash
python -c "
from app import create_app
from models import db, User, Film
app = create_app()
with app.app_context():
    u = User(username='alice', email='alice@example.com')
    f1 = Film(title='Parasite', year=2019, director='Bong Joon-ho')
    f2 = Film(title='Annihilation', year=2018, director='Alex Garland')
    db.session.add_all([u, f1, f2])
    db.session.commit()
    print('user_id:', u.id)
    print('film1_id:', f1.id)
    print('film2_id:', f2.id)
"
```

Then test the watchlist endpoints (substitute the UUIDs printed above):

```bash
# Add a film to the watchlist
curl -X POST http://127.0.0.1:5000/watchlist/1/add \
  -H 'Content-Type: application/json' \
  -d '{"film_id": "<film1_uuid>"}'

# Add a second film
curl -X POST http://127.0.0.1:5000/watchlist/1/add \
  -H 'Content-Type: application/json' \
  -d '{"film_id": "<film2_uuid>"}'

# Get watchlist — most recently added appears first
curl http://127.0.0.1:5000/watchlist/1

# Add the same film again — returns the existing entry (no duplicate)
curl -X POST http://127.0.0.1:5000/watchlist/1/add \
  -H 'Content-Type: application/json' \
  -d '{"film_id": "<film1_uuid>"}'
```

## Running tests

```bash
pytest tests/ -v
```

## Data model

- **Film.id** is a UUID string (`String(36)`, auto-generated). Film IDs are UUIDs in all requests and responses.
- **Collection** — join table between User and Film; tracks films a user has watched.
- **WatchlistEntry** — tracks films a user intends to watch; has a `public` flag (defaults to `True`).

## Design decisions

**Watchlist visibility defaults to `public=True`:** CineLog is a community platform — the social value of a watchlist is letting friends see what you want to watch next. Users who want privacy can set `public=False` explicitly.

**Watchlist sort order is date-added descending:** A watchlist is a queue of intent, not a reference shelf. The most recently added films reflect current interest and should appear first. (The collection uses alphabetical sort because it is a historical record you browse by title.)

## Branch structure

| Branch | Contents |
|--------|----------|
| `main` | Full CineLog app including watchlist feature |
| `feature/watchlist` | Watchlist feature PR — addresses 6 code-review comments, rebases on UUID refactor, includes `pr-response.md` |
