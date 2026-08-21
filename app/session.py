"""Per-call session assembly. Pure and deterministic (except voice choice) so it
can be unit-tested without any network or API key."""
import random

from . import tech_support_training as tst

# Natural gpt-realtime voices only, paired with a gender so the customer sim
# matches the voice. Older voices (echo/shimmer/ash) sound robotic and are excluded.
VOICES = [
    {"voice": "marin", "gender": "female"},
    {"voice": "cedar", "gender": "male"},
]

# Agent (AI rep) names, chosen to match the voice gender so a female voice never
# gets a male name and vice versa.
AGENT_NAMES = {
    "female": ["Sarah", "Emily", "Jessica", "Rachel", "Ashley", "Megan", "Lauren", "Hannah"],
    "male": ["Michael", "David", "Chris", "Daniel", "Ryan", "Kevin", "Brian", "Jason"],
}


def _join(*parts):
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def build_session(mode, settings, difficulty="easy"):
    """Assemble the per-call spec for a given mode.

    training: AI plays the simulated customer; the human is the support agent and
              greets first. Customer identity/difficulty come from the reused sim;
              the admin `customer_system_prompt` is layered on as extra steering.
    agent:    AI is the support agent and greets first; the human is the caller.
              Uses the admin `agent_system_prompt`.
    """
    chosen = random.choice(VOICES)
    platform = settings.get("system_prompt")

    if mode == "training":
        customer = tst.generate_tech_customer(gender=chosen["gender"])
        base, customer_data = tst.get_tech_support_prompt(
            difficulty=difficulty, customer=customer
        )
        instructions = _join(settings.get("customer_system_prompt"), base, platform)
        return {
            "mode": mode,
            "instructions": instructions,
            "voice": chosen["voice"],
            "greeter": "user",
            "customer": customer_data,
        }

    if mode == "agent":
        name = random.choice(AGENT_NAMES[chosen["gender"]])
        identity = (
            f"For this call your name is {name} and you are located in Austin, Texas. "
            f"Introduce yourself with this exact name and never use any other name."
        )
        instructions = _join(identity, settings.get("agent_system_prompt"), platform)
        return {
            "mode": mode,
            "instructions": instructions,
            "voice": chosen["voice"],
            "greeter": "ai",
            "name": name,
            "customer": None,
        }

    raise ValueError(f"unknown mode: {mode}")
