import importlib.util
import json
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "scripts" / "github_monitor.py"
    spec = importlib.util.spec_from_file_location("github_monitor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_monitor_recovers_from_corrupt_state_and_formats_pull_request_context(tmp_path, monkeypatch):
    monitor = _module()
    state = tmp_path / "state.json"
    state.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(monitor, "STATE", state)
    assert monitor._load_state() == set()
    event = {
        "type": "PullRequestReviewEvent",
        "actor": {"login": "other-dev"},
        "payload": {"action": "submitted", "pull_request": {"number": 42, "title": "Improve SEO"}},
    }
    assert monitor._event_message(event) == (
        "Shorts Pipeline GitHub activity",
        "other-dev: PullRequestReview #42 Improve SEO (submitted)",
    )


def test_monitor_saves_state_atomically(tmp_path, monkeypatch):
    monitor = _module()
    state = tmp_path / "nested" / "state.json"
    monkeypatch.setattr(monitor, "STATE", state)
    monitor._save_state({"event-2", "event-1"})
    assert json.loads(state.read_text(encoding="utf-8")) == ["event-1", "event-2"]
    assert not state.with_suffix(".json.tmp").exists()


def test_monitor_fetches_events_over_bounded_https(monkeypatch):
    monitor = _module()
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"id": "event-1", "type": "PushEvent"}]

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(monitor.httpx, "get", fake_get)

    assert monitor.fetch_events() == [{"id": "event-1", "type": "PushEvent"}]
    assert calls == [
        (
            "https://api.github.com/repos/Subset28/shorts-pipeline/events",
            {
                "params": {"per_page": 30},
                "headers": {"Accept": "application/vnd.github+json", "User-Agent": "shorts-pipeline-monitor"},
                "timeout": 15,
            },
        )
    ]
