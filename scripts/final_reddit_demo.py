"""Render the final local Reddit-story lane demo without publishing it."""

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
        hook="I accidentally took down our company's production database.",
        narration=(
            "I accidentally took down our company's production database. "
            "I was cleaning up an old staging environment during an overnight "
            "maintenance window, but the script matched the production hostname "
            "too. The site was down for eleven minutes before we restored the "
            "backup, and now every deployment requires a second person to approve "
            "the command."
        ),
        title="I accidentally took down our company's production database.",
        card_text="I accidentally took down our company's production database.",
        description=(
            "Reddit attribution: u/demo_story in r/TalesFromTechSupport\n"
            "Local layout demo only; not for publishing."
        ),
        sources=["https://www.reddit.com/r/TalesFromTechSupport/comments/demo/"],
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
