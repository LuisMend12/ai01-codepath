from flask import Blueprint, request, jsonify
from services.collection_service import add_to_collection, get_collection

collection_bp = Blueprint("collection", __name__, url_prefix="/collection")


@collection_bp.route("/<int:user_id>", methods=["GET"])
def get_user_collection(user_id):
    try:
        entries = get_collection(user_id)
        return jsonify(entries), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@collection_bp.route("/<int:user_id>/add", methods=["POST"])
def add_film_to_collection(user_id):
    data = request.get_json()
    if not data or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400
    try:
        entry = add_to_collection(user_id, data["film_id"])
        return jsonify({
            "message": "Added to collection",
            "entry_id": entry.id,
            "film_id": entry.film_id,
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
