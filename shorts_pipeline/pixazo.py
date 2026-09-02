"""Bounded Pixazo media-generation adapter.

This module intentionally supports one configured provider credential. It is not
a key/account rotator and must not be used to evade provider quotas or terms.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

ALLOWED_OPERATIONS = {"text-to-video", "image-to-video", "video-to-video"}
DEFAULT_BASE_URL = "https://gateway.pixazo.ai"


@dataclass(frozen=True)
class PixazoRequest:
    request_id: str
    model: str
    operation: str
    prompt: str


def pixazo_configuration_issues(*, enabled: bool, api_key: str, daily_request_limit: int) -> list[str]:
    if not enabled:
        return []
    if not api_key.strip():
        return ["pixazo_api_key_missing"]
    if daily_request_limit < 1:
        return ["pixazo_daily_request_limit_invalid"]
    return []


class PixazoClient:
    def __init__(
        self,
        api_key: str,
        state_path: Path,
        *,
        enabled: bool,
        daily_request_limit: int,
        allowed_models: tuple[str, ...] = ("ltx",),
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        issues = pixazo_configuration_issues(enabled=enabled, api_key=api_key, daily_request_limit=daily_request_limit)
        if issues and enabled:
            raise ValueError(", ".join(issues))
        self._api_key = api_key
        self._state_path = state_path
        self._enabled = enabled
        self._daily_request_limit = daily_request_limit
        self._allowed_models = tuple(sorted({item.strip() for item in allowed_models if item.strip()}))
        self._base_url = base_url.rstrip("/")

    def submit(self, request: PixazoRequest) -> dict[str, Any]:
        if not self._enabled:
            raise RuntimeError("Pixazo generation is disabled")
        self._validate_request(request)
        with self._state_lock():
            state = self._load_state()
            completed = state.get("completed", {}).get(request.request_id)
            if isinstance(completed, dict):
                return completed
            today = datetime.now(timezone.utc).date().isoformat()
            usage = state.get("usage", {})
            if usage.get("date") != today:
                usage = {"date": today, "requests": 0}
            if int(usage.get("requests", 0)) >= self._daily_request_limit:
                raise RuntimeError("Pixazo daily request limit reached")
            response = self._post(request)
            result = self._result(request, response)
            usage["requests"] = int(usage.get("requests", 0)) + 1
            state["usage"] = usage
            state.setdefault("completed", {})[request.request_id] = {
                **result,
                "output_url": _safe_output_url(str(result["output_url"])),
                "polling_url": _safe_output_url(str(result["polling_url"])),
            }
            self._save_state(state)
            return result

    def status(self) -> dict[str, Any]:
        state = self._load_state()
        return {
            "enabled": self._enabled,
            "configured": bool(self._api_key),
            "key_fingerprint": self._fingerprint(),
            "daily_request_limit": self._daily_request_limit,
            "allowed_models": list(self._allowed_models),
            "usage": state.get("usage", {}),
        }

    def _validate_request(self, request: PixazoRequest) -> None:
        if not request.request_id.strip() or not request.prompt.strip():
            raise ValueError("Pixazo request_id and prompt are required")
        if request.model not in self._allowed_models:
            raise ValueError(f"Pixazo model is not allowed: {request.model}")
        if request.operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"Pixazo operation is not allowed: {request.operation}")

    def _post(self, request: PixazoRequest) -> dict[str, Any]:
        model_path = "ltx-video/v1" if request.model == "ltx" else f"{request.model}/v1"
        endpoint = f"{self._base_url}/{model_path}/{request.operation}"
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Idempotency-Key": request.request_id,
        }
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.post(endpoint, headers=headers, json={"prompt": request.prompt})
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Pixazo returned an invalid response")
        return payload

    def _result(self, request: PixazoRequest, payload: dict[str, Any]) -> dict[str, Any]:
        nested = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        output_url = str(payload.get("url") or payload.get("output_url") or nested.get("url") or "").strip()
        job_id = str(
            payload.get("id")
            or payload.get("job_id")
            or payload.get("request_id")
            or nested.get("id")
            or nested.get("request_id")
            or ""
        ).strip()
        polling_url = str(payload.get("polling_url") or nested.get("polling_url") or "").strip()
        if not output_url and not job_id:
            raise RuntimeError("Pixazo response contains no output URL or job ID")
        return {
            "request_id": request.request_id,
            "provider": "pixazo",
            "model": request.model,
            "operation": request.operation,
            "job_id": job_id,
            "output_url": output_url,
            "polling_url": polling_url,
            "key_fingerprint": self._fingerprint(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _load_state(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"usage": {}, "completed": {}}
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Pixazo usage state cannot be read") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Pixazo usage state is invalid")
        usage = payload.get("usage", {})
        completed = payload.get("completed", {})
        if not isinstance(usage, dict) or not isinstance(completed, dict):
            raise RuntimeError("Pixazo usage state is invalid")
        return payload

    @contextmanager
    def _state_lock(self):
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self._state_path.with_suffix(f"{self._state_path.suffix}.lock")
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _save_state(self, state: dict[str, Any]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(f"{self._state_path.suffix}.tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self._state_path)

    def _fingerprint(self) -> str:
        return hashlib.sha256(self._api_key.encode("utf-8")).hexdigest()[:12] if self._api_key else ""


def _safe_output_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
