from flask import Blueprint, current_app, render_template

bp = Blueprint("agent", __name__, url_prefix="/agent")


@bp.route("/")
def index():
    """Agentic Call Center Agent. Tool calls (device health, etc.) are a later phase."""
    return render_template(
        "agent.html",
        agent_prompt=current_app.settings.get("agent_system_prompt"),
    )
