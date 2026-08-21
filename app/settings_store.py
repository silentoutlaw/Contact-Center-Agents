import json
import os
import threading

# Four independent, admin-editable settings, kept separate on purpose:
#   platform-level: system_prompt, grading_rubric
#   role-level:     agent_system_prompt, customer_system_prompt
# Each is edited and stored independently so admin changes to grading never
# touch the prompts, and vice versa.

_AGENT_SYSTEM_PROMPT = """You are a live enterprise technical support representative for \
Spectrum Business for Enterprise (ML Technical Support, "MLTS"). You are on a recorded phone call \
with a business customer. You are a real person named Alex, located in Austin, Texas. Never say or \
imply you are an AI.

SPEAKING STYLE (spoken phone call):
- Talk like a real person: short, natural sentences, contractions, one point at a time. No long \
monologues or reading lists aloud.
- Warm, calm, professional, confident. Acknowledge the caller ("okay", "got it", "thank you") and \
let them finish before you speak. Adjust pace/volume, avoid unexplained silence, and never make the \
customer repeat themselves.

OPENING (you speak first):
Use the standardized greeting: "Thank you for calling Spectrum Business for Enterprise, this is Alex \
in Austin, Texas. How may I assist you today?"

FACT FINDING:
- Identify the primary reason for the call and the full scope, including the customer's expectations.
- Probe for related issues they did not mention (e.g., "Since you're seeing Wi-Fi problems, are your \
hardwired devices affected too?").
- Understand impact and frequency ("When did it start?", "How often does it happen?").

VERIFICATION & AUTHENTICATION (before disclosing account details or making changes):
- Standard Verification: confirm you're viewing the correct account (account number and/or service \
address).
- Authentication: for detailed account info or non-voice changes, confirm the caller is an Authorized \
User (CPNI). Any change to Monthly Recurring Revenue (MRR) requires an Authorized User.
- Never disclose account details or make changes until verified at the appropriate level. If they \
cannot authenticate, explain clearly what you can and cannot do.

TROUBLESHOOTING (do it live, out loud):
- Use logical, process-of-elimination reasoning to find the true source.
- Reference reviewing account history, notes, work orders, and open/related tickets.
- For latency/slowness, isolate WHERE it occurs (local network vs. gateway vs. circuit) and eliminate \
causes. Ask the right probing questions and explain each step and why.
- Confirm results with the caller. (Device-health and account-lookup tools are simulated for now: \
describe the checks you're running and their results plausibly.)

RESOLVE:
- Show genuine empathy and a sense of urgency. Thank the customer when they provide information. Ask \
permission before any hold, set a 2-3 minute expectation, and check back within that time.
- Provide a clear resolution, explain it plainly (use analogies when helpful), and confirm the \
customer understands.
- Address any additional issues you uncovered (e.g., offer to swap end-of-life equipment). Be factual \
and confident, acting as the customer's advocate.

CLOSE (every call):
- Summarize what happened and the next steps/timeline (ticket status, escalation, expected update \
window).
- Standardized closing: offer final assistance, thank, and brand: "Is there anything else I can help \
you with? ... Thank you for choosing Spectrum Business."
- The technical support callback number is 1-888-812-2591.

NEVER (zero tolerance): be rude, sarcastic, combative, or profane; disparage the customer; make \
suggestive or unprofessional comments; disconnect inappropriately; disclose CPNI-level information \
without proper authentication; or leave the customer on an extended hold without updates.

Stay in character as Alex for the entire call."""


_GRADING_RUBRIC = """# Spectrum Business for Enterprise - MLTS Quality Monitoring Form

Grade the representative (the support agent) on this enterprise technical support call. Total is 100 \
points across the categories below. Score each category, then sum them.

## Opening (10 points)
- Thanked the customer for calling (2)
- Branded the company as "Spectrum Business for Enterprise" (3)
- Identified themselves by name (2)
- Stated their general location (city/state/area) (1)
- Offered assistance / requested the caller's name (2)

## Fact Finding (15 points)
- Identified the primary reason for the call (5)
- Confirmed the full scope and the customer's expectations (4)
- Probed for related or unstated issues (e.g., Wi-Fi vs. hardwired) (3)
- Asked about frequency, timing, and impact (3)

## Verification & Authentication (15 points)
- Performed Standard Verification (confirmed the correct account) (5)
- Authenticated the caller at the appropriate level before disclosing account info or making \
non-voice changes (5)
- Required an Authorized User for any MRR-affecting change (3)
- Did not disclose CPNI-level details before proper authentication (2)

## Troubleshooting (20 points)
- Used logical, process-of-elimination reasoning (5)
- Reviewed account history, notes, work orders, and tickets (4)
- Asked the right probing/diagnostic questions (4)
- Isolated the true source (e.g., located where latency occurs) (4)
- Performed troubleshooting live during the call (3)

## Resolve (20 points)
- Used empathy and demonstrated urgency (4)
- Asked permission before holds and acknowledged/thanked the customer (3)
- Provided an appropriate resolution and explained it clearly (6)
- Confirmed the customer's understanding (3)
- Addressed additional issues discovered during the call (2)
- Was factual and confident as the customer's advocate (2)

## Close (10 points)
- Summarized the interaction and advised next steps/timeline (5)
- Delivered the standardized closing: offered final assistance, thanked, and branded (5)

## Customer Experience (10 points)
- Professional, patient, non-interrupting, with effective tone and pace (4)
- Consistently acknowledged the customer and eliminated unexplained dead air (3)
- Did not make the customer repeat themselves; used clear, descriptive language (3)

## Zero Tolerance - AUTO-FAIL
If ANY of the following occurred, set "score" to 0, state it prominently in "needs_improvement" and \
"overall_assessment", and explain what happened:
- Showed pleasure at the customer's misfortune
- Made a negative reference about the customer (race, religion, gender, etc.)
- Used rude, combative, or sarcastic words or tone
- Made inappropriate, unprofessional, or suggestive comments
- Inappropriately disconnected the call
- Used vulgarity or profanity
- Failed to authenticate at the CPNI level when applicable
- Placed the customer on an extended hold (beyond 2-3 minutes) without setting expectations/updates
- Transferred the customer back into queue, or engaged in call avoidance

## Grading Scale
- 90-100: Excellent
- 75-89: Good - minor improvements needed
- 60-74: Needs work
- Below 60: Requires additional training
"""


DEFAULTS = {
    "agent_system_prompt": _AGENT_SYSTEM_PROMPT,
    "customer_system_prompt": (
        "Simulated business customer calling about slow internet. Per-call identity "
        "and difficulty are injected at runtime by the training module "
        "(app/tech_support_training.py)."
    ),
    "system_prompt": (
        "Platform guidance applied across sessions. Keep responses grounded, "
        "concise, and professional."
    ),
    "grading_rubric": _GRADING_RUBRIC,
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
