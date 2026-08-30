from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Settings


def synthesize(text: str, settings: Settings, output: Path) -> Path | None:
    """Use the existing rotating ElevenLabs helper without importing its keys.

    Missing rotator configuration is a normal free-mode condition; the render
    stage will produce a silent draft rather than failing the whole run.
    """
    if not settings.elevenlabs_voice_id or not settings.elevenlabs_rotator_path.exists():
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "python",
        str(settings.elevenlabs_rotator_path),
        "--text", text,
        "--voice-id", settings.elevenlabs_voice_id,
        "--model-id", settings.elevenlabs_model_id,
        "--out", str(output),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"TTS unavailable; continuing with silent draft: {exc}")
        return None
    return output if output.exists() and output.stat().st_size else None
