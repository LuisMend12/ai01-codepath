from flask import Blueprint, jsonify, request
from services import song_service

bp = Blueprint("songs", __name__, url_prefix="/songs")


@bp.get("/")
def list_songs():
    return jsonify(song_service.get_all_songs())


@bp.get("/search")
def search():
    q = request.args.get("q", "")
    return jsonify(song_service.search_songs(q))


@bp.post("/<int:song_id>/listen")
def listen(song_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    return jsonify(song_service.record_listen(user_id, song_id))


@bp.post("/<int:song_id>/rate")
def rate(song_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    rating = data.get("rating")
    if not user_id or rating is None:
        return jsonify({"error": "user_id and rating required"}), 400
    result = song_service.rate_song(user_id, song_id, int(rating))
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)
