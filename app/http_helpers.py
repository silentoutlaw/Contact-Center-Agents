"""Shared Flask helpers so the training and agent blueprints stay DRY."""
from flask import current_app, jsonify, request

from . import openai_client as oc
from .session import build_session


def start_session_response(mode):
    """Return the per-call session spec. No API key goes to the browser; the
    server relays the Realtime connection (see app/relay.py)."""
    key = oc.load_api_key()
    if not key:
        return jsonify(error="OpenAI API key not configured"), 500
    difficulty = (request.get_json(silent=True) or {}).get("difficulty", "easy")
    spec = build_session(mode, current_app.settings, difficulty)
    return jsonify(spec)


def grade_response():
    """Grade a posted transcript against the admin-configured rubric."""
    key = oc.load_api_key()
    if not key:
        return jsonify(error="OpenAI API key not configured"), 500
    transcript = (request.get_json(silent=True) or {}).get("transcript", "")
    if not transcript.strip():
        return jsonify(error="transcript required"), 400
    rubric = current_app.settings.get("grading_rubric")
    try:
        return jsonify(oc.grade(key, transcript, rubric))
    except Exception as e:  # network / API failure
        return jsonify(error=f"grading failed: {e}"), 502
