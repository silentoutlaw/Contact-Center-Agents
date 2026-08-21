import os


class Config:
    """Environment-driven config. Runs on 443 with SSL by default."""

    HOST = os.environ.get("CCA_HOST", "0.0.0.0")
    PORT = int(os.environ.get("CCA_PORT", "443"))
    SSL_CERT = os.environ.get("CCA_SSL_CERT", "certs/server.crt")
    SSL_KEY = os.environ.get("CCA_SSL_KEY", "certs/server.key")
    DATA_DIR = os.environ.get("CCA_DATA_DIR", "data")
    # CEILING: a random per-restart secret invalidates sessions on every restart.
    # Upgrade: set CCA_SECRET_KEY to a stable value in the environment for production.
    SECRET_KEY = os.environ.get("CCA_SECRET_KEY", os.urandom(32).hex())

    @classmethod
    def ssl_context(cls):
        """Return (cert, key) if both exist, else None so dev can fall back to http."""
        if os.path.exists(cls.SSL_CERT) and os.path.exists(cls.SSL_KEY):
            return (cls.SSL_CERT, cls.SSL_KEY)
        return None
