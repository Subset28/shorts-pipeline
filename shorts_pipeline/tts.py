from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .config import Settings
from .resources import ffmpeg_resource_args

TTS_PROVIDERS = {"auto", "elevenlabs", "edge", "macos"}


def tts_configuration_issues(settings: Settings) -> list[str]:
    provider = str(getattr(settings, "tts_provider", "auto")).strip().lower()
    if provider not in TTS_PROVIDERS:
        return ["tts_provider_unsupported"]
    if provider == "macos":
        issues = []
        voice = str(getattr(settings, "macos_tts_voice", "")).strip()
        if not voice:
            issues.append("macos_voice_missing")
        has_say = bool(shutil.which("say"))
        if not has_say:
            issues.append("macos_say_missing")
        elif voice:
            try:
                result = subprocess.run(
                    ["say", "-v", "?"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                issues.append("macos_voice_query_failed")
            else:
                if not any(line.startswith(f"{voice} ") for line in result.stdout.splitlines()):
                    issues.append("macos_voice_unavailable")
        if not shutil.which("ffmpeg"):
            issues.append("ffmpeg_missing")
        return issues

    rotator = getattr(settings, "elevenlabs_rotator_path", Path())
    voice = str(getattr(settings, "elevenlabs_voice_id", "")).strip()
    has_rotator = isinstance(rotator, Path) and rotator.is_file()
    has_elevenlabs_hint = bool(voice or has_rotator)
    if provider == "elevenlabs" or (provider == "auto" and has_elevenlabs_hint):
        issues = []
        if not voice:
            issues.append("elevenlabs_voice_missing")
        if not has_rotator:
            issues.append("elevenlabs_rotator_missing")
        return issues
    if not str(getattr(settings, "edge_tts_voice", "")).strip():
        return ["edge_tts_voice_missing"]
    return []


def _macos_synthesize(text: str, settings: Settings, output: Path) -> Path | None:
    intermediate = output.with_suffix(".aiff")
    intermediate.unlink(missing_ok=True)
    try:
        subprocess.run(
            [
                "say",
                "-v",
                str(settings.macos_tts_voice),
                "-r",
                str(settings.macos_tts_rate),
                "-o",
                str(intermediate),
                text,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                *ffmpeg_resource_args(1),
                "-i",
                str(intermediate),
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"macOS TTS unavailable: {type(exc).__name__}")
        output.unlink(missing_ok=True)
        return None
    finally:
        intermediate.unlink(missing_ok=True)
    return output if output.exists() and output.stat().st_size else None


def synthesize(text: str, settings: Settings, output: Path) -> Path | None:
    """Use the existing rotating ElevenLabs helper without importing its keys.

    Missing rotator configuration is a normal free-mode condition. When
    ElevenLabs is configured but unavailable, stop instead of silently
    downgrading a premium channel to a different voice.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    provider = str(getattr(settings, "tts_provider", "auto")).strip().lower()
    if provider not in TTS_PROVIDERS:
        raise ValueError(f"Unsupported TTS provider: {provider}")
    if provider == "macos":
        return _macos_synthesize(text, settings, output)
    has_elevenlabs_hint = bool(settings.elevenlabs_voice_id or settings.elevenlabs_rotator_path.is_file())
    use_elevenlabs = provider == "elevenlabs" or (provider == "auto" and has_elevenlabs_hint)
    if use_elevenlabs:
        if not settings.elevenlabs_voice_id or not settings.elevenlabs_rotator_path.is_file():
            print("ElevenLabs unavailable: configuration missing")
            return None
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
    if provider not in {"auto", "edge"}:
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
