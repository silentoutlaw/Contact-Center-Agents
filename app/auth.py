"""Session-based auth for a single bootstrap admin.

Credentials come from the environment (CCA_ADMIN_USER / CCA_ADMIN_PASSWORD),
which are loaded from the project .env. Read at request time so the check always
reflects current config and stays easy to test.
"""
from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("auth", __name__)


def _safe_next(target):
    """Only allow local redirects to avoid open-redirect abuse."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("training.index")


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if current_app.credentials.verify(request.form.get("username", ""),
                                          request.form.get("password", "")):
            session.clear()
            session["user"] = request.form.get("username", "")
            return redirect(_safe_next(request.args.get("next", "")))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
