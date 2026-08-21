"""Runnable self-check for the settings store (no test framework).

    python tests/test_settings_store.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings_store import DEFAULTS, SettingsStore


def main():
    with tempfile.TemporaryDirectory() as d:
        store = SettingsStore(os.path.join(d, "settings.json"))

        # Defaults are present before anything is saved.
        assert store.get("grading_rubric") == DEFAULTS["grading_rubric"]
        assert set(store.all()) == set(DEFAULTS)

        # A saved value overrides only its own key; others stay default.
        store.set("agent_system_prompt", "custom agent")
        assert store.get("agent_system_prompt") == "custom agent"
        assert store.get("customer_system_prompt") == DEFAULTS["customer_system_prompt"]

        # Persistence: a fresh store reads the saved override from disk.
        reopened = SettingsStore(os.path.join(d, "settings.json"))
        assert reopened.get("agent_system_prompt") == "custom agent"

        # Unknown keys are rejected at the trust boundary.
        try:
            store.set("not_a_key", "x")
        except KeyError:
            pass
        else:
            raise AssertionError("expected KeyError for unknown setting key")

    print("OK: settings store defaults, override isolation, persistence, key guard")


if __name__ == "__main__":
    main()
