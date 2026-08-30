"""
ElevenLabs TTS key rotator.

Cycles through a pool of your own ElevenLabs API keys. Uses one key until
it reports quota exhaustion, then moves to the next. An exhausted key is
skipped for a cooldown period (default 30 days) before being retried,
matching ElevenLabs' monthly quota reset.

Setup:
    pip install requests

Create keys.json next to this script:
    [
      {"label": "acct-1", "key": "xi-api-key-1"},
      {"label": "acct-2", "key": "xi-api-key-2"}
    ]

Usage:
    python elevenlabs_tts_rotator.py --text "Hello world" --voice-id EXAVITQu4vr4xnSDxMaL --out out.mp3
    python elevenlabs_tts_rotator.py --status   # show key cooldown state
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
KEYS_FILE = Path(os.getenv("ELEVENLABS_KEYS_FILE", SCRIPT_DIR / "keys.json"))
STATE_FILE = SCRIPT_DIR / "key_state.json"
COOLDOWN_DAYS = 30
API_BASE = "https://api.elevenlabs.io/v1"


def load_keys():
    if not KEYS_FILE.exists():
        sys.exit(f"Missing {KEYS_FILE}. Create it with your ElevenLabs keys (see script docstring).")
    return json.loads(KEYS_FILE.read_text(encoding="utf-8"))


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_available(label, state):
    exhausted_at = state.get(label, {}).get("exhausted_at")
    if not exhausted_at:
        return True
    exhausted_dt = datetime.fromisoformat(exhausted_at)
    return datetime.now(timezone.utc) >= exhausted_dt + timedelta(days=COOLDOWN_DAYS)


def mark_exhausted(label, state):
    state[label] = {"exhausted_at": datetime.now(timezone.utc).isoformat()}
    save_state(state)


def remaining_cooldown(label, state):
    exhausted_at = state.get(label, {}).get("exhausted_at")
    if not exhausted_at:
        return None
    exhausted_dt = datetime.fromisoformat(exhausted_at)
    ready_at = exhausted_dt + timedelta(days=COOLDOWN_DAYS)
    delta = ready_at - datetime.now(timezone.utc)
    return delta if delta.total_seconds() > 0 else None


def check_quota(key):
    """Return (character_count, character_limit) from /v1/user, or None if the call fails."""
    resp = requests.get(f"{API_BASE}/user", headers={"xi-api-key": key}, timeout=15)
    if resp.status_code != 200:
        return None
    sub = resp.json().get("subscription", {})
    return sub.get("character_count"), sub.get("character_limit")


def synthesize(text, voice_id, out_path, model_id="eleven_multilingual_v2"):
    keys = load_keys()
    state = load_state()

    for entry in keys:
        label, key = entry["label"], entry["key"]

        if not is_available(label, state):
            cooldown = remaining_cooldown(label, state)
            print(f"[skip] {label}: cooling down, {cooldown.days}d left", file=sys.stderr)
            continue

        quota = check_quota(key)
        if quota:
            used, limit = quota
            if limit and used + len(text) > limit:
                print(f"[skip] {label}: would exceed quota ({used}/{limit} chars)", file=sys.stderr)
                mark_exhausted(label, state)
                continue

        print(f"[try] {label}", file=sys.stderr)
        resp = requests.post(
            f"{API_BASE}/text-to-speech/{voice_id}",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": model_id},
            timeout=60,
        )

        if resp.status_code == 200:
            Path(out_path).write_bytes(resp.content)
            print(f"[ok] {label} -> {out_path}", file=sys.stderr)
            return

        body = resp.text.lower()
        if resp.status_code in (401, 429) and ("quota" in body or "limit" in body):
            print(f"[exhausted] {label}: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            mark_exhausted(label, state)
            continue

        # Non-quota error (bad request, invalid voice, etc.) - don't burn the key, just fail loud.
        sys.exit(f"[error] {label}: {resp.status_code} {resp.text[:300]}")

    sys.exit("All keys exhausted or cooling down. See --status.")


def print_status():
    keys = load_keys()
    state = load_state()
    for entry in keys:
        label = entry["label"]
        if is_available(label, state):
            quota = check_quota(entry["key"])
            quota_str = f"{quota[0]}/{quota[1]} chars used" if quota else "quota check failed"
            print(f"{label}: available ({quota_str})")
        else:
            cooldown = remaining_cooldown(label, state)
            print(f"{label}: cooling down, {cooldown.days}d {cooldown.seconds // 3600}h left")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="Text to synthesize")
    ap.add_argument("--voice-id", help="ElevenLabs voice ID")
    ap.add_argument("--out", default="output.mp3", help="Output audio file path")
    ap.add_argument("--model-id", default="eleven_multilingual_v2")
    ap.add_argument("--status", action="store_true", help="Show key availability/cooldown state and exit")
    args = ap.parse_args()

    if args.status:
        print_status()
        return

    if not args.text or not args.voice_id:
        sys.exit("--text and --voice-id are required (or use --status)")

    synthesize(args.text, args.voice_id, args.out, args.model_id)


if __name__ == "__main__":
    main()
