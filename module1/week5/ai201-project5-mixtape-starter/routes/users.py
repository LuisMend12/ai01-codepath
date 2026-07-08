from flask import Blueprint, jsonify
from services import user_service

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.get("/<int:user_id>/streak")
def streak(user_id):
    return jsonify(user_service.get_streak(user_id))


@bp.get("/<int:user_id>/notifications")
def notifications(user_id):
    return jsonify(user_service.get_notifications(user_id))
