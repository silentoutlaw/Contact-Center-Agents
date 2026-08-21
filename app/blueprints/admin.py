from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Each setting is editable independently (granular by design).
EDITABLE = [
    "agent_system_prompt",
    "customer_system_prompt",
    "system_prompt",
    "grading_rubric",
]


@bp.route("/", methods=["GET", "POST"])
def index():
    store = current_app.settings
    if request.method == "POST":
        key = request.form.get("key", "")
        if key in EDITABLE:  # trust boundary: only allow known keys
            store.set(key, request.form.get("value", ""))
        return redirect(url_for("admin.index"))
    return render_template(
        "admin.html", settings={k: store.get(k) for k in EDITABLE}
    )
