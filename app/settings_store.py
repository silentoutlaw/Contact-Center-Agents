import json
import os
import threading

from . import tech_support_training as tst

# Four independent, admin-editable settings, kept separate on purpose:
#   platform-level: system_prompt, grading_rubric
#   role-level:     agent_system_prompt, customer_system_prompt
# Each is edited and stored independently so admin changes to grading never
# touch the prompts, and vice versa.
DEFAULTS = {
    "agent_system_prompt": (
        "You are a professional contact center technical support agent helping a "
        "business caller with an internet/connectivity issue. Verify the caller, "
        "diagnose methodically, explain clearly, and resolve or escalate."
    ),
    "customer_system_prompt": (
        "Simulated business customer calling about slow internet. Per-call identity "
        "and difficulty are injected at runtime by the training module "
        "(app/tech_support_training.py)."
    ),
    "system_prompt": (
        "Platform guidance applied across sessions. Keep responses grounded, "
        "concise, and professional."
    ),
    "grading_rubric": tst.DEFAULT_TECH_STEERING,
}


class SettingsStore:
    """JSON-backed settings. Saved values override DEFAULTS key-by-key."""

    def __init__(self, path):
        self.path = path
        # CEILING: process-local lock only, not safe across multiple worker
        # processes. Upgrade: a DB row or an OS file lock (flock) when scaling out.
        self._lock = threading.Lock()

    def _read(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def all(self):
        return {**DEFAULTS, **self._read()}

    def get(self, key):
        return self.all().get(key)

    def set(self, key, value):
        if key not in DEFAULTS:
            raise KeyError(f"unknown setting: {key}")
        with self._lock:
            data = self._read()
            data[key] = value
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)  # atomic write; never leaves a half file
