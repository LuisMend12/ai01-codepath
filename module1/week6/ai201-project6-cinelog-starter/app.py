from flask import Flask
from models import db


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cinelog.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from routes.collection.collection import collection_bp
    from routes.watchlist.watchlist import watchlist_bp
    app.register_blueprint(collection_bp)
    app.register_blueprint(watchlist_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
