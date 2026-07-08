"""Mixtape — Flask application factory.

Start with:
    FLASK_APP=app:create_app flask run

Do NOT use `python app.py` — that triggers a SQLAlchemy double-import error.
"""

from flask import Flask
from models import db


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mixtape.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from routes.users import bp as users_bp
    from routes.songs import bp as songs_bp
    from routes.playlists import bp as playlists_bp
    from routes.feed import bp as feed_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(songs_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(feed_bp)

    with app.app_context():
        db.create_all()

    return app
