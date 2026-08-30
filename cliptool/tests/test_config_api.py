import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point config at a throwaway copy so tests never mutate the real config.json
    real_config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    tmp_config = tmp_path / "config.json"
    tmp_config.write_text(json.dumps(real_config), encoding="utf-8")

    import cliptool.config as config_mod
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_config)

    from api.app import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "twitch_configured" in body["secrets"]
    assert "youtube_configured" in body["secrets"]


def test_get_config_never_exposes_secrets(client):
    resp = client.get("/config")
    assert resp.status_code == 200
    body = resp.json()
    assert "min_clip_seconds" in body
    dumped = json.dumps(body)
    assert "TWITCH_CLIENT_SECRET" not in dumped
    assert "YOUTUBE_API_KEY" not in dumped


def test_put_config_updates_value(client):
    resp = client.put("/config", json={"patch": {"min_clip_seconds": 12}})
    assert resp.status_code == 200
    assert resp.json()["min_clip_seconds"] == 12

    resp2 = client.get("/config")
    assert resp2.json()["min_clip_seconds"] == 12


def test_put_config_rejects_unknown_key(client):
    resp = client.put("/config", json={"patch": {"totally_made_up_key": 1}})
    assert resp.status_code == 400


def test_put_config_rejects_invalid_range(client):
    resp = client.put("/config", json={"patch": {"min_clip_seconds": 500, "max_clip_seconds": 10}})
    assert resp.status_code == 400


def test_config_schema_lists_editable_fields(client):
    resp = client.get("/config/schema")
    assert resp.status_code == 200
    body = resp.json()
    assert "scoring_weights" in body
    assert "_secrets" in body
