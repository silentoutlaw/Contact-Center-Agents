"""Runnable self-check for the settings store (no test framework).

    python tests/test_settings_store.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.settings_store import DEFAULTS, SettingsStore
from app.session import build_session


class _FakeSettings:
    def __init__(self, values):
        self._v = values

    def get(self, key):
        return self._v.get(key)


def check_session_building():
    settings = _FakeSettings({
        "customer_system_prompt": "CUSTOMER_MARK",
        "agent_system_prompt": "AGENT_MARK",
        "system_prompt": "PLATFORM_MARK",
        "grading_rubric": "RUBRIC",
    })

    # Training: AI is the customer, human greets first, no backchannel, has customer data.
    t = build_session("training", settings, difficulty="easy")
    assert t["greeter"] == "user"
    assert t["backchannel"] is False
    assert t["customer"] and t["customer"]["account"].startswith("8")
    assert "CUSTOMER_MARK" in t["instructions"]
    assert "PLATFORM_MARK" in t["instructions"]
    assert "AGENT_MARK" not in t["instructions"]  # agent prompt must not leak in

    # Agent: AI greets first, backchannel on, uses agent prompt not customer prompt.
    a = build_session("agent", settings)
    assert a["greeter"] == "ai"
    assert a["backchannel"] is True
    assert a["customer"] is None
    assert "AGENT_MARK" in a["instructions"]
    assert "CUSTOMER_MARK" not in a["instructions"]

    try:
        build_session("bogus", settings)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown mode")

    print("OK: session building, prompt isolation between roles, greeter/backchannel")


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
    check_session_building()


if __name__ == "__main__":
    main()
