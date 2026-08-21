import os

from flask import Flask, redirect, url_for

from .config import Config
from .settings_store import SettingsStore


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(Config.DATA_DIR, exist_ok=True)

    # Single shared settings store; admin panel reads/writes it.
    app.settings = SettingsStore(os.path.join(Config.DATA_DIR, "settings.json"))

    from .blueprints.training import bp as training_bp
    from .blueprints.agent import bp as agent_bp
    from .blueprints.admin import bp as admin_bp

    app.register_blueprint(training_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_bp)

    @app.route("/")
    def index():
        return redirect(url_for("training.index"))

    return app
