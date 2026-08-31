from __future__ import annotations

import os


def ffmpeg_resource_args() -> list[str]:
    """Return conservative FFmpeg limits for unattended media jobs."""
    try:
        requested = int(os.getenv("FFMPEG_THREADS", "2"))
    except ValueError:
        requested = 2
    threads = min(4, max(1, requested))
    return [
        "-threads",
        str(threads),
        "-filter_threads",
        "1",
        "-filter_complex_threads",
        "1",
    ]
