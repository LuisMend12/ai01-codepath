from flask import Blueprint, request, jsonify
from services.watchlist_service import add_to_watchlist, get_watchlist

watchlist_bp = Blueprint("watchlist", __name__, url_prefix="/watchlist")


@watchlist_bp.route("/<int:user_id>", methods=["GET"])
def get_user_watchlist(user_id):
    try:
        entries = get_watchlist(user_id)
        return jsonify(entries), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@watchlist_bp.route("/<int:user_id>/add", methods=["POST"])
def add_film_to_watchlist(user_id):
    data = request.get_json()
    if not data or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400
    try:
        entry = add_to_watchlist(user_id, data["film_id"])
        return jsonify({
            "message": "Added to watchlist",
            "entry_id": entry.id,
            "film_id": entry.film_id,
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
