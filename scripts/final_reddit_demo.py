"""Render the final local Reddit-story lane demo without publishing it."""

from pathlib import Path

from shorts_pipeline.captions import create_captions
from shorts_pipeline.config import load_settings
from shorts_pipeline.media import select_backgrounds
from shorts_pipeline.models import ScriptPackage
from shorts_pipeline.render import render_video
from shorts_pipeline.tts import synthesize


def main() -> None:
    settings = load_settings()
    output = settings.output_dir / "final-reddit-demo"
    output.mkdir(parents=True, exist_ok=True)
    package = ScriptPackage(
        hook="He told me to reject a $120K promotion.",
        narration=(
            "My boyfriend told me to reject a one hundred twenty thousand dollar "
            "promotion because it would make him look bad. He said I needed to "
            "decline the job and take a receptionist position instead. So I "
            "demoted him as an ex."
        ),
        title=(
            "My boyfriend told me to reject a $120K promotion because it would "
            "make him look bad. He said I need to decline the job and take a "
            "receptionist position instead. So, I DEMOTED him as an EX."
        ),
        card_text=(
            "My boyfriend told me to reject a $120K promotion because it would "
            "make him look bad. He said I need to decline the job and take a "
            "receptionist position instead. So, I DEMOTED him as an EX."
        ),
        description=(
            "Reddit attribution: u/demo_story in r/relationship_advice\n"
            "Local layout demo only; not for publishing."
        ),
        sources=["https://www.reddit.com/"],
        format_name="reddit_story",
        category="Reddit Stories",
    )
    audio = synthesize(package.narration, settings, output / "narration.mp3")
    if not audio or not audio.exists() or audio.stat().st_size == 0:
        raise RuntimeError("Demo TTS produced no audio")
    captions = create_captions(
        package.narration, audio, output / "captions.srt", settings.caption_model
    )
    backgrounds = select_backgrounds(settings.reddit_background_dir, package.title, limit=1)
    background = backgrounds[0] if backgrounds else None
    video = render_video(package, output, audio, captions, background)
    print(video)


if __name__ == "__main__":
    main()
