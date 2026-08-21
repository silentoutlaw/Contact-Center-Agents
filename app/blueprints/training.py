from flask import Blueprint, current_app, render_template

bp = Blueprint("training", __name__, url_prefix="/training")


@bp.route("/")
def index():
    """Technical Support Call Training. Reuses the customer simulation module.

    Voice/barge-in handling and live LLM wiring are a later phase.
    """
    return render_template(
        "training.html",
        customer_prompt=current_app.settings.get("customer_system_prompt"),
    )
