"""Admin credential storage.

Precedence: if data/credentials.json exists, verify against its salted PBKDF2
hash. Otherwise fall back to the .env bootstrap (CCA_ADMIN_USER / _PASSWORD).
This lets the first login work from .env and lets the admin change the password
persistently without storing plaintext.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading

_ITERATIONS = 200_000


def _pbkdf2(password, salt_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _ITERATIONS
    ).hex()


class Credentials:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "credentials.json")
        self._lock = threading.Lock()

    def _read(self):
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def username(self):
        stored = self._read()
        if stored:
            return stored["username"]
        return os.environ.get("CCA_ADMIN_USER")

    def verify(self, username, password):
        """Constant-time check against the stored hash, else the .env bootstrap."""
        stored = self._read()
        if stored:
            calc = _pbkdf2(password or "", stored["salt"])
            ok_user = hmac.compare_digest(username or "", stored["username"])
            ok_pass = hmac.compare_digest(calc, stored["hash"])
            return ok_user and ok_pass
        u = os.environ.get("CCA_ADMIN_USER")
        p = os.environ.get("CCA_ADMIN_PASSWORD")
        if not u or not p:
            return False
        return (hmac.compare_digest(username or "", u)
                and hmac.compare_digest(password or "", p))

    def set_password(self, new_password, username=None):
        salt = secrets.token_hex(16)
        data = {
            "username": username or self.username(),
            "salt": salt,
            "hash": _pbkdf2(new_password, salt),
        }
        with self._lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, self.path)
            os.chmod(self.path, 0o600)
