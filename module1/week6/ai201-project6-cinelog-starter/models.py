import uuid

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


class Film(db.Model):
    __tablename__ = "films"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    director = db.Column(db.String(200))

    def __repr__(self):
        return f"<Film {self.title} ({self.year})>"


class Collection(db.Model):
    """Films a user has already watched."""

    __tablename__ = "collections"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    film_id = db.Column(db.String(36), db.ForeignKey("films.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("collections", lazy="dynamic"))
    film = db.relationship("Film", backref=db.backref("collected_by", lazy="dynamic"))


class WatchlistEntry(db.Model):
    """Films a user intends to watch."""

    __tablename__ = "watchlist"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    film_id = db.Column(db.String(36), db.ForeignKey("films.id"), nullable=False)
    public = db.Column(db.Boolean, default=True, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("watchlist", lazy="dynamic"))
    film = db.relationship("Film", backref=db.backref("watchlisted_by", lazy="dynamic"))
