from concurrent.futures import ThreadPoolExecutor
from time import sleep

import httpx
import pytest

from shorts_pipeline import cli
from shorts_pipeline.config import load_settings
from shorts_pipeline.pixazo import PixazoClient, PixazoRequest, pixazo_configuration_issues


def _request() -> PixazoRequest:
    return PixazoRequest(
        request_id="shot-001",
        model="ltx",
        operation="text-to-video",
        prompt="abstract network packets becoming a clear dependency graph",
    )


def test_pixazo_requires_explicit_enablement_and_a_daily_cap(tmp_path):
    assert pixazo_configuration_issues(enabled=False, api_key="", daily_request_limit=0) == []
    assert pixazo_configuration_issues(enabled=True, api_key="", daily_request_limit=5) == ["pixazo_api_key_missing"]
    assert pixazo_configuration_issues(enabled=True, api_key="key", daily_request_limit=0) == [
        "pixazo_daily_request_limit_invalid"
    ]


def test_pixazo_rejects_disabled_or_disallowed_requests(tmp_path):
    client = PixazoClient("key", tmp_path / "usage.json", enabled=False, daily_request_limit=2)
    with pytest.raises(RuntimeError, match="disabled"):
        client.submit(_request())
    enabled = PixazoClient("key", tmp_path / "usage.json", enabled=True, daily_request_limit=2, allowed_models=("ltx",))
    with pytest.raises(ValueError, match="not allowed"):
        enabled.submit(PixazoRequest("shot-002", "veo", "text-to-video", "prompt"))


def test_pixazo_submits_once_and_records_secret_safe_provenance(tmp_path, monkeypatch):
    calls = []

    def fake_post(self, url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            200, json={"id": "job-1", "url": "https://media.example/clip.mp4"}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = PixazoClient("top-secret-key", tmp_path / "usage.json", enabled=True, daily_request_limit=2)
    result = client.submit(_request())
    duplicate = client.submit(_request())
    assert result == duplicate
    assert len(calls) == 1
    assert calls[0][1]["headers"]["Ocp-Apim-Subscription-Key"] == "top-secret-key"
    assert result["provider"] == "pixazo"
    assert result["output_url"] == "https://media.example/clip.mp4"
    assert "top-secret-key" not in str(result)
    assert "top-secret-key" not in (tmp_path / "usage.json").read_text(encoding="utf-8")


def test_pixazo_daily_cap_stops_new_submissions(tmp_path, monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(
            200,
            json={"id": kwargs["headers"]["Idempotency-Key"], "url": "https://media.example/clip.mp4"},
            request=httpx.Request("POST", url),
        ),
    )
    client = PixazoClient("key", tmp_path / "usage.json", enabled=True, daily_request_limit=1)
    client.submit(_request())
    with pytest.raises(RuntimeError, match="daily request limit"):
        client.submit(PixazoRequest("shot-002", "ltx", "text-to-video", "second prompt"))


def test_pixazo_fails_closed_when_existing_usage_state_is_invalid(tmp_path):
    state_path = tmp_path / "usage.json"
    state_path.write_text("not-json", encoding="utf-8")
    client = PixazoClient("key", state_path, enabled=True, daily_request_limit=1)
    with pytest.raises(RuntimeError, match="usage state"):
        client.submit(_request())


def test_pixazo_fails_closed_when_usage_state_has_invalid_structure(tmp_path):
    state_path = tmp_path / "usage.json"
    state_path.write_text('{"usage": [], "completed": {}}', encoding="utf-8")
    client = PixazoClient("key", state_path, enabled=True, daily_request_limit=1)
    with pytest.raises(RuntimeError, match="usage state"):
        client.submit(_request())


def test_pixazo_serializes_concurrent_submissions_under_the_daily_cap(tmp_path, monkeypatch):
    def fake_post(self, url, **kwargs):
        sleep(0.05)
        return httpx.Response(
            200,
            json={"id": kwargs["headers"]["Idempotency-Key"], "url": "https://media.example/clip.mp4"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = PixazoClient("key", tmp_path / "usage.json", enabled=True, daily_request_limit=1)
    requests = (_request(), PixazoRequest("shot-002", "ltx", "text-to-video", "second prompt"))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda request: _submit_result(client, request), requests))
    assert sum(result == "ok" for result in results) == 1
    assert sum("daily request limit" in result for result in results) == 1


def _submit_result(client, request):
    try:
        client.submit(request)
    except RuntimeError as exc:
        return str(exc)
    return "ok"


def test_pixazo_strips_signed_output_url_before_persisting(tmp_path, monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(
            200,
            json={"id": "job-1", "url": "https://media.example/clip.mp4?signature=private"},
            request=httpx.Request("POST", url),
        ),
    )
    state_path = tmp_path / "usage.json"
    PixazoClient("key", state_path, enabled=True, daily_request_limit=1).submit(_request())
    state = state_path.read_text(encoding="utf-8")
    assert "signature" not in state
    assert "https://media.example/clip.mp4" in state


def test_pixazo_settings_are_disabled_by_default_and_keep_the_key_out_of_paths(monkeypatch):
    monkeypatch.setenv("PIXAZO_ENABLED", "true")
    monkeypatch.setenv("PIXAZO_API_KEY", "test-only-key")
    monkeypatch.setenv("PIXAZO_DAILY_REQUEST_LIMIT", "3")
    monkeypatch.setenv("PIXAZO_STATE_FILE", "data/pixazo_usage.json")
    settings = load_settings()
    assert settings.pixazo_enabled is True
    assert settings.pixazo_api_key == "test-only-key"
    assert settings.pixazo_daily_request_limit == 3
    assert settings.pixazo_state_file.name == "pixazo_usage.json"


def test_pixazo_status_reports_configuration_without_exposing_key(monkeypatch, tmp_path, capsys):
    settings = type(
        "Settings",
        (),
        {
            "pixazo_enabled": True,
            "pixazo_api_key": "test-only-key",
            "pixazo_state_file": tmp_path / "usage.json",
            "pixazo_daily_request_limit": 2,
            "pixazo_allowed_models": ("ltx",),
            "pixazo_base_url": "https://gateway.pixazo.ai",
        },
    )()
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    assert cli.run_pixazo_status() == 0
    output = capsys.readouterr().out
    assert '"requested_enabled": true' in output
    assert "test-only-key" not in output
