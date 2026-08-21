from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
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

MIN_PASSWORD_LEN = 6


def _render(**extra):
    store = current_app.settings
    return render_template(
        "admin.html", settings={k: store.get(k) for k in EDITABLE}, **extra
    )


@bp.route("/", methods=["GET", "POST"])
def index():
    store = current_app.settings
    if request.method == "POST":
        key = request.form.get("key", "")
        if key in EDITABLE:  # trust boundary: only allow known keys
            store.set(key, request.form.get("value", ""))
        return redirect(url_for("admin.index"))
    return _render()


@bp.route("/password", methods=["POST"])
def change_password():
    creds = current_app.credentials
    user = session.get("user")
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not creds.verify(user, current):
        return _render(pw_error="Current password is incorrect."), 400
    if len(new) < MIN_PASSWORD_LEN:
        return _render(
            pw_error=f"New password must be at least {MIN_PASSWORD_LEN} characters."
        ), 400
    if new != confirm:
        return _render(pw_error="New passwords do not match."), 400

    creds.set_password(new, username=user)
    return _render(pw_success="Password updated.")
