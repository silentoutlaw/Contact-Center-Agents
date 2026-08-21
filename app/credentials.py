"""Admin credential storage (multi-user).

Precedence: if data/credentials.json exists, verify against its salted PBKDF2
hashes. Otherwise fall back to the .env bootstrap (CCA_ADMIN_USER / _PASSWORD).
This lets the first login work from .env and lets admins change passwords and
add users persistently without storing plaintext.
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
        """Return list of user dicts, migrating single-user format if needed."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        # Migrate old single-user format {"username":..., "salt":..., "hash":...}
        if isinstance(data, dict) and "username" in data:
            data = [data]
            self._write(data)
        return data

    def _write(self, users):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)

    def _find(self, username):
        for u in self._read():
            if u["username"] == username:
                return u
        return None

    def username(self):
        """Return the first stored username (for display), or the env bootstrap."""
        users = self._read()
        if users:
            return users[0]["username"]
        return os.environ.get("CCA_ADMIN_USER")

    def verify(self, username, password):
        """Constant-time check against stored hash, else the .env bootstrap."""
        user = self._find(username or "")
        if user:
            calc = _pbkdf2(password or "", user["salt"])
            return hmac.compare_digest(calc, user["hash"])
        # Fallback to .env bootstrap if no stored users at all
        if not self._read():
            u = os.environ.get("CCA_ADMIN_USER")
            p = os.environ.get("CCA_ADMIN_PASSWORD")
            if not u or not p:
                return False
            return (hmac.compare_digest(username or "", u)
                    and hmac.compare_digest(password or "", p))
        return False

    def set_password(self, new_password, username=None):
        salt = secrets.token_hex(16)
        entry = {
            "username": username or self.username(),
            "salt": salt,
            "hash": _pbkdf2(new_password, salt),
        }
        with self._lock:
            users = self._read()
            # Update existing or append new
            for i, u in enumerate(users):
                if u["username"] == entry["username"]:
                    users[i] = entry
                    self._write(users)
                    return
            users.append(entry)
            self._write(users)
