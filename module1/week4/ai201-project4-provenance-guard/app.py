"""Provenance Guard — Flask API.

See planning.md for architecture, signal design, and label/threshold spec.
"""

import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import storage
from detection.labels import render_label
from detection.llm_signal import analyze_with_llm
from detection.scoring import classify, combine_scores
from detection.stylometric_signal import analyze_stylometry

load_dotenv()
storage.init_db()

app = Flask(__name__)

# Rate limiting rationale (see README "Rate Limiting" section):
# 8/minute allows a writer to retry/resubmit edited drafts in one sitting
# without enabling a flood; 60/day bounds Groq API cost and storage growth
# while comfortably covering a prolific single creator's daily output.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/submit", methods=["POST"])
@limiter.limit("8 per minute;60 per day")
def submit():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    creator_id = data.get("creator_id", "").strip()

    if not text or not creator_id:
        return jsonify({"error": "text and creator_id are required"}), 400

    content_id = str(uuid.uuid4())

    llm_result = analyze_with_llm(text)
    stylometric_result = analyze_stylometry(text)

    llm_score = llm_result["llm_score"]
    stylometric_score = stylometric_result["stylometric_score"]
    confidence = combine_scores(llm_score, stylometric_score)
    attribution = classify(confidence)
    label = render_label(attribution, confidence)

    timestamp = storage.save_submission(
        content_id, creator_id, text, llm_score, stylometric_score,
        confidence, attribution, label,
    )

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signals": {
            "llm_score": llm_score,
            "llm_reasoning": llm_result["reasoning"],
            "stylometric_score": stylometric_score,
            "stylometric_metrics": stylometric_result["metrics"],
        },
        "status": "classified",
    })


@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = data.get("content_id", "").strip()
    creator_reasoning = data.get("creator_reasoning", "").strip()

    if not content_id or not creator_reasoning:
        return jsonify({"error": "content_id and creator_reasoning are required"}), 400

    timestamp = storage.file_appeal(content_id, creator_reasoning)
    if timestamp is None:
        return jsonify({"error": f"content_id {content_id} not found"}), 404

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "timestamp": timestamp,
        "message": "Appeal received and logged. Content status set to under_review.",
    })


@app.route("/log", methods=["GET"])
def log():
    limit = request.args.get("limit", default=50, type=int)
    return jsonify({"entries": storage.get_log(limit)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
