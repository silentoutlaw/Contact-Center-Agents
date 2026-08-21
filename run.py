from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    # Binding to 443 requires privilege. Either run behind a reverse proxy, or grant
    # the interpreter the capability once:
    #   sudo setcap 'cap_net_bind_service=+ep' $(readlink -f $(which python3))
    # If no cert/key is present, ssl_context() returns None and Flask serves http
    # (useful for local dev only, never expose http in production).
    app.run(host=Config.HOST, port=Config.PORT, ssl_context=Config.ssl_context())
