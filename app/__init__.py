import os

from flask import Flask, redirect, request, url_for
from flask import session as flask_session

from .config import Config
from .settings_store import SettingsStore

# Endpoints reachable without a session.
_PUBLIC_ENDPOINTS = {"auth.login", "static"}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(Config.DATA_DIR, exist_ok=True)

    # Single shared settings store; admin panel reads/writes it.
    app.settings = SettingsStore(os.path.join(Config.DATA_DIR, "settings.json"))

    from .auth import bp as auth_bp
    from .blueprints.training import bp as training_bp
    from .blueprints.agent import bp as agent_bp
    from .blueprints.admin import bp as admin_bp
    from .relay import sock

    app.register_blueprint(auth_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_bp)
    sock.init_app(app)  # registers the /ws/realtime relay

    @app.before_request
    def require_login():
        if request.endpoint in _PUBLIC_ENDPOINTS:
            return
        if not flask_session.get("user"):
            return redirect(url_for("auth.login", next=request.path))

    @app.route("/")
    def index():
        return redirect(url_for("training.index"))

    return app
