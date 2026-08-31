from __future__ import annotations

import os


def ffmpeg_resource_args(thread_override: int | None = None) -> list[str]:
    """Return conservative FFmpeg limits for unattended media jobs."""
    if thread_override is None:
        try:
            requested = int(os.getenv("FFMPEG_THREADS", "2"))
        except ValueError:
            requested = 2
    else:
        requested = thread_override
    threads = min(4, max(1, requested))
    return [
        "-threads",
        str(threads),
        "-filter_threads",
        "1",
        "-filter_complex_threads",
        "1",
    ]
