from flask import Blueprint, jsonify, request
from services import playlist_service

bp = Blueprint("playlists", __name__, url_prefix="/playlists")


@bp.post("/")
def create():
    data = request.get_json() or {}
    name = data.get("name")
    created_by = data.get("created_by")
    if not name or not created_by:
        return jsonify({"error": "name and created_by required"}), 400
    return jsonify(playlist_service.create_playlist(name, created_by)), 201


@bp.get("/<int:playlist_id>")
def get_playlist(playlist_id):
    return jsonify(playlist_service.get_playlist(playlist_id))


@bp.get("/<int:playlist_id>/songs")
def songs(playlist_id):
    return jsonify(playlist_service.get_playlist_songs(playlist_id))


@bp.post("/<int:playlist_id>/songs")
def add_song(playlist_id):
    data = request.get_json() or {}
    song_id = data.get("song_id")
    added_by = data.get("added_by")
    if not song_id or not added_by:
        return jsonify({"error": "song_id and added_by required"}), 400
    return jsonify(playlist_service.add_song_to_playlist(playlist_id, song_id, added_by)), 201
