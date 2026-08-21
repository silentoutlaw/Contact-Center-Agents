from flask import Blueprint, current_app, render_template

from ..http_helpers import grade_response, start_session_response

bp = Blueprint("training", __name__, url_prefix="/training")


@bp.route("/")
def index():
    """Technical Support Call Training. Human is the agent; AI plays the customer."""
    return render_template(
        "training.html",
        customer_prompt=current_app.settings.get("customer_system_prompt"),
    )


@bp.route("/session", methods=["POST"])
def session():
    return start_session_response("training")


@bp.route("/grade", methods=["POST"])
def grade():
    return grade_response()
