from flask import Blueprint, current_app, render_template

from ..http_helpers import start_session_response

bp = Blueprint("agent", __name__, url_prefix="/agent")


@bp.route("/")
def index():
    """Agentic Call Center Agent. AI is the support agent; human is the caller.

    Tool calls (device health, etc.) are a planned later phase.
    """
    return render_template(
        "agent.html",
        agent_prompt=current_app.settings.get("agent_system_prompt"),
    )


@bp.route("/session", methods=["POST"])
def session():
    return start_session_response("agent")
