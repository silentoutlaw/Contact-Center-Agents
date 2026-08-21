"""Session-based auth for a single bootstrap admin.

Credentials come from the environment (CCA_ADMIN_USER / CCA_ADMIN_PASSWORD),
which are loaded from the project .env. Read at request time so the check always
reflects current config and stays easy to test.
"""
import hmac
import os

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("auth", __name__)


def check_credentials(username, password):
    """Constant-time credential check against the configured admin."""
    u = os.environ.get("CCA_ADMIN_USER")
    p = os.environ.get("CCA_ADMIN_PASSWORD")
    if not u or not p:
        return False
    ok_user = hmac.compare_digest(username or "", u)
    ok_pass = hmac.compare_digest(password or "", p)
    return ok_user and ok_pass


def _safe_next(target):
    """Only allow local redirects to avoid open-redirect abuse."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("training.index")


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if check_credentials(request.form.get("username", ""),
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
