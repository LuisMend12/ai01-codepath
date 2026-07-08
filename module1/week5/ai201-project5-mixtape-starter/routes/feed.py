from flask import Blueprint, jsonify
from services import feed_service

bp = Blueprint("feed", __name__, url_prefix="/feed")


@bp.get("/<int:user_id>/listening-now")
def listening_now(user_id):
    return jsonify(feed_service.get_friends_listening_now(user_id))
