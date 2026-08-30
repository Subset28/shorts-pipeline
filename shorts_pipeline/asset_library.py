from __future__ import annotations

import json
import os
from pathlib import Path

import httpx


def load_asset_manifest(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("asset manifest must contain an assets list")
    required = {"name", "filename", "url", "source_page", "attribution", "rights_note"}
    for asset in assets:
        if not isinstance(asset, dict) or not required.issubset(asset):
            raise ValueError("each asset must include name, filename, url, source_page, attribution, and rights_note")
    return assets


def sync_backgrounds(manifest_path: Path, output_dir: Path) -> list[Path]:
    """Download only explicitly cataloged assets, atomically and resumably."""
    assets = load_asset_manifest(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for asset in assets:
        target = output_dir / Path(asset["filename"]).name
        if target.exists() and target.stat().st_size:
            downloaded.append(target)
            continue
        if asset["url"].startswith("local://"):
            # Local user-supplied footage is cataloged for selection but is
            # copied into the library separately; never treat its placeholder
            # URL as a network download.
            continue
        # Deployment and Container Manager can invoke a sync concurrently.
        # A shared ``.part`` path lets one process remove/replace another's
        # download before the atomic rename. Keep each in-flight transfer
        # isolated; completed targets remain atomically replaced.
        temporary = target.with_name(f"{target.name}.{os.getpid()}.part")
        with httpx.stream("GET", asset["url"], follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        temporary.replace(target)
        downloaded.append(target)
    return downloaded
