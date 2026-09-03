"""
Pixazo API key rotator.

Cycles through a pool of your own Pixazo API keys. Uses one key until
it reports quota exhaustion, then moves to the next. An exhausted key is
skipped for a cooldown period (default 30 days) before being retried,
matching typical monthly billing cycles.

Setup:
    Create keys.json next to this script:
    [
      {"label": "acct-1", "key": "your-api-key-1"},
      {"label": "acct-2", "key": "your-api-key-2"}
    ]

Usage:
    python pixazo_rotator.py --prompt "a cat" --model ltx --operation text-to-video --out out.mp4
    python pixazo_rotator.py --status   # show key cooldown state
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
KEYS_FILE = Path(os.getenv("PIXAZO_KEYS_FILE", SCRIPT_DIR / "pixazo_keys.json"))
STATE_FILE = SCRIPT_DIR / "pixazo_rotator_state.json"
COOLDOWN_DAYS = 30
DEFAULT_BASE_URL = "https://gateway.pixazo.ai"


def load_keys():
    if not KEYS_FILE.exists():
        sys.exit(f"Missing {KEYS_FILE}. Create it with your Pixazo keys (see script docstring).")
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


def check_balance(key):
    """Return remaining balance or None if check fails."""
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(
                f"{DEFAULT_BASE_URL}/account/balance",
                headers={"Ocp-Apim-Subscription-Key": key},
            )
            if response.status_code != 200:
                return None
            data = response.json()
            if isinstance(data, dict):
                return data.get("balance") or data.get("remaining_credits")
    except Exception:
        pass
    return None


def submit_request(prompt, model, operation, request_id, base_url=DEFAULT_BASE_URL):
    keys = load_keys()
    state = load_state()

    for entry in keys:
        label, key = entry["label"], entry["key"]

        if not is_available(label, state):
            cooldown = remaining_cooldown(label, state)
            print(f"[skip] {label}: cooling down, {cooldown.days}d left", file=sys.stderr)
            continue

        balance = check_balance(key)
        if balance is not None and balance <= 0:
            print(f"[skip] {label}: no balance remaining", file=sys.stderr)
            mark_exhausted(label, state)
            continue

        print(f"[try] {label}", file=sys.stderr)
        model_path = "ltx-video/v1" if model == "ltx" else f"{model}/v1"
        endpoint = f"{base_url.rstrip('/')}/{model_path}/{operation}"
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": key,
            "Idempotency-Key": request_id,
        }

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(endpoint, headers=headers, json={"prompt": prompt})

                if response.status_code == 200:
                    result = response.json()
                    print(f"[ok] {label} -> {endpoint}", file=sys.stderr)
                    return result

                body = response.text.lower()
                if response.status_code in (401, 429) and ("quota" in body or "limit" in body or "balance" in body):
                    print(f"[exhausted] {label}: {response.status_code} {response.text[:200]}", file=sys.stderr)
                    mark_exhausted(label, state)
                    continue

                sys.exit(f"[error] {label}: {response.status_code} {response.text[:300]}")
        except Exception as exc:
            sys.exit(f"[error] {label}: {exc}")

    sys.exit("All keys exhausted or cooling down. See --status.")


def print_status():
    keys = load_keys()
    state = load_state()
    for entry in keys:
        label = entry["label"]
        if is_available(label, state):
            balance = check_balance(entry["key"])
            balance_str = f"{balance} credits" if balance is not None else "balance check failed"
            print(f"{label}: available ({balance_str})")
        else:
            cooldown = remaining_cooldown(label, state)
            print(f"{label}: cooling down, {cooldown.days}d {cooldown.seconds // 3600}h left")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", help="Text prompt for generation")
    ap.add_argument("--model", default="ltx", help="Model to use (default: ltx)")
    ap.add_argument("--operation", default="text-to-video", help="Operation type (default: text-to-video)")
    ap.add_argument("--request-id", help="Unique request ID (default: auto-generated)")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Pixazo base URL (default: {DEFAULT_BASE_URL})")
    ap.add_argument("--status", action="store_true", help="Show key availability/cooldown state and exit")
    args = ap.parse_args()

    if args.status:
        print_status()
        return

    if not args.prompt:
        sys.exit("--prompt is required (or use --status)")

    request_id = args.request_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:20]
    result = submit_request(args.prompt, args.model, args.operation, request_id, args.base_url)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
