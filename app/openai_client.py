"""Thin OpenAI helpers over stdlib urllib (no SDK dependency).

Covers the three things this app needs server-side:
  * loading the API key,
  * minting a short-lived Realtime key for the browser (with fallback),
  * grading a transcript against an admin-configured rubric.
"""
import json
import os
import urllib.request

# Realtime model used for the browser WebSocket connection.
REALTIME_MODEL = os.environ.get("CCA_REALTIME_MODEL", "gpt-realtime-2.1")
# Model used for post-call grading.
GRADING_MODEL = os.environ.get("CCA_GRADING_MODEL", "gpt-4o")

# Legacy key locations, kept for reuse with the existing project setup.
_LEGACY_ENV_FILES = [
    os.path.expanduser("~/.env"),
    os.path.expanduser("~/truskills-crm/.env"),
]
_KEY_PREFIXES = ("OPENAI_API_KEY=", "OpenAIKey=")


def load_api_key():
    """Return the OpenAI key from env, else from a legacy .env file, else None."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key.strip()
    for path in _LEGACY_ENV_FILES:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                for prefix in _KEY_PREFIXES:
                    if line.startswith(prefix):
                        return line[len(prefix):].strip()
    return None


def _post(url, key, payload, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mint_realtime_key(key, instructions, voice):
    """Mint a short-lived ephemeral Realtime key; fall back to the standing key.

    CEILING: the fallback hands a standing API key to the browser, which is only
    acceptable on a trusted/local network. Upgrade path: require the ephemeral
    endpoint to succeed and put the app behind authentication before exposing it.
    """
    try:
        resp = _post(
            "https://api.openai.com/v1/realtime/sessions",
            key,
            {"model": REALTIME_MODEL, "voice": voice, "instructions": instructions},
        )
        secret = (resp.get("client_secret") or {}).get("value")
        if secret:
            return {"key": secret, "ephemeral": True}
    except Exception:
        # Endpoint unavailable or errored; fall back to the standing key.
        pass
    return {"key": key, "ephemeral": False}


_GRADE_SYSTEM = """You are a call-center training evaluator. Grade the transcript \
strictly against the scoring guide below.

SCORING GUIDE:
{rubric}

Respond as JSON:
{{
  "score": <0-100 integer>,
  "breakdown": {{"<category>": <points>}},
  "did_well": ["specific examples"],
  "needs_improvement": ["specific examples"],
  "suggested_phrases": ["better phrasing they could have used"],
  "overall_assessment": "one short paragraph"
}}"""


def grade(key, transcript, rubric):
    """Grade a transcript against the rubric. Returns parsed JSON dict."""
    resp = _post(
        "https://api.openai.com/v1/chat/completions",
        key,
        {
            "model": GRADING_MODEL,
            "temperature": 0.3,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _GRADE_SYSTEM.format(rubric=rubric)},
                {"role": "user", "content": f"Transcript to grade:\n\n{transcript}"},
            ],
        },
    )
    return json.loads(resp["choices"][0]["message"]["content"])
