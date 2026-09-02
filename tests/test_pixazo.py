from datetime import datetime, timezone

import httpx
import pytest

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
        return httpx.Response(200, json={"id": "job-1", "url": "https://media.example/clip.mp4"}, request=httpx.Request("POST", url))

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
            200, json={"id": kwargs["json"]["request_id"], "url": "https://media.example/clip.mp4"}, request=httpx.Request("POST", url)
        ),
    )
    client = PixazoClient("key", tmp_path / "usage.json", enabled=True, daily_request_limit=1)
    client.submit(_request())
    with pytest.raises(RuntimeError, match="daily request limit"):
        client.submit(PixazoRequest("shot-002", "ltx", "text-to-video", "second prompt"))
