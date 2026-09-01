from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .config import Settings


def synthesize(text: str, settings: Settings, output: Path) -> Path | None:
    """Use the existing rotating ElevenLabs helper without importing its keys.

    Missing rotator configuration is a normal free-mode condition. When
    ElevenLabs is configured but unavailable, stop instead of silently
    downgrading a premium channel to a different voice.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    if settings.elevenlabs_voice_id and settings.elevenlabs_rotator_path.exists():
        # Use the interpreter running the pipeline so Windows installs do not
        # depend on a separate `python` command being on PATH.
        command = [
            sys.executable,
            str(settings.elevenlabs_rotator_path),
            "--text",
            text,
            "--voice-id",
            settings.elevenlabs_voice_id,
            "--model-id",
            settings.elevenlabs_model_id,
            "--out",
            str(output),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
            if output.exists() and output.stat().st_size:
                return output
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"ElevenLabs unavailable; refusing lower-quality voice fallback: {type(exc).__name__}")
            return None
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "edge_tts",
                "--voice",
                settings.edge_tts_voice,
                "--text",
                text,
                "--write-media",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"TTS unavailable; continuing with silent draft: {exc}")
    return output if output.exists() and output.stat().st_size else None
