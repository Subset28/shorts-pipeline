import json

from shorts_pipeline.cli import run_competitor_research


def test_competitor_research_cli_writes_sorted_git_safe_packet(tmp_path, capsys):
    records = []
    for index in range(10):
        records.append(
            {
                "channel_id": f"channel-{index}",
                "video_id": f"video-{index}",
                "published_at": "2026-08-31T00:00:00Z",
                "views": 1000,
                "likes": 10,
                "comments": 2,
                "hook_archetype": "reversal" if index < 3 else "",
            }
        )
    source = tmp_path / "metadata.json"
    target = tmp_path / "nested" / "packet.json"
    source.write_text(json.dumps(records), encoding="utf-8")
    assert run_competitor_research(source, target, "2026-09-01T00:00:00Z") == 0
    assert json.loads(target.read_text(encoding="utf-8"))["cohort"]["channel_count"] == 10
    assert "Wrote competitor research packet" in capsys.readouterr().out
