import hashlib
import re

from .models import ScriptPackage, Topic

ALLOWED_FORMATS = (
    "news_breakdown",
    "fact_explainer",
    "myth_bust",
    "technical_joke",
    "surprising_fact",
    "timeline",
    "question_answer",
    "prediction_watch",
    "reddit_story",
)


def eligible_formats(topic: Topic) -> tuple[str, ...]:
    """Return lanes whose promise can be supported by this source."""
    source = topic.sources[0]
    text = f"{topic.title} {topic.sources[0].summary}".lower()
    formats = ["news_breakdown", "fact_explainer", "question_answer"]
    if topic.category in {"AI", "ML", "CS", "AI News", "Cyber"}:
        formats.insert(2, "technical_joke")
    myth_signal = re.search(r"\b(myth|false|wrong|debunk|misconception|claim|actually|really|true|doesn['’]t|not)\b", text)
    if myth_signal:
        formats.insert(2, "myth_bust")
    surprise_signal = re.search(
        r"\b(first|only|largest|smallest|unexpected|surprising|record|breakthrough)\b|\b\d+(?:\.\d+)?%\b|\b\d+x\b",
        text,
    )
    if surprise_signal:
        formats.append("surprising_fact")
    timeline_signal = re.search(
        r"\b(first|then|after|before|timeline|history|since|announced|launched|approved|earlier|later)\b",
        text,
    )
    if timeline_signal:
        formats.append("timeline")
    prediction_signal = re.search(
        r"\b(will|could|may|might|expects?|forecast|predict(?:s|ed|ion)?|plans?|claims?|projected|outlook)\b",
        text,
    )
    if prediction_signal:
        formats.append("prediction_watch")
    if (
        source.url.lower().startswith(("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/"))
        and source.author
        and source.community
        and source.reuse_permission
    ):
        formats.append("reddit_story")
    return tuple(formats)


def fallback_package(topic: Topic, variant: int = 0) -> ScriptPackage:
    source = topic.sources[0]
    title = topic.title[:85]
    formats = eligible_formats(topic)
    if "reddit_story" in formats and variant == 0:
        format_name = "reddit_story"
    else:
        format_index = (int(hashlib.sha256(source.url.encode("utf-8")).hexdigest()[:2], 16) + max(0, variant)) % len(formats)
        format_name = formats[format_index]
    headline = re.sub(r"\s+", " ", source.title).strip().rstrip(".")
    # The source title remains in narration/metadata; the on-screen hook needs
    # to stay scannable on a phone instead of becoming a tiny headline block.
    headline = headline[:42].rsplit(" ", 1)[0] if len(headline) > 42 else headline
    hook_templates = {
        "news_breakdown": "What '{headline}' actually means",
        "fact_explainer": "The simple explanation of '{headline}'",
        "myth_bust": "What '{headline}' gets wrong",
        "technical_joke": "POV: '{headline}' reaches production",
        "surprising_fact": "The detail in '{headline}' that changes the story",
        "question_answer": "What does '{headline}' actually mean?",
        "timeline": "How '{headline}' got here",
        "prediction_watch": "Will '{headline}' actually happen?",
        "reddit_story": "The config change that took down an office",
    }
    hook = hook_templates[format_name].format(headline=headline)
    summary = " ".join(source.summary.split())
    if len(summary.split()) < 8:
        # Some RSS feeds, especially link aggregators, provide only URLs and
        # engagement counts. The title is safer and more intelligible than
        # narrating feed boilerplate or inventing missing context.
        summary = source.title
    if format_name == "reddit_story":
        # Preserve enough of the source to reach its outcome without inventing
        # a resolution. Trim only at a complete sentence boundary.
        if len(summary) > 900:
            summary = summary[:900].rsplit(".", 1)[0].rstrip() + "."
    elif len(summary) > 560:
        summary = summary[:560].rsplit(" ", 1)[0] + "..."
    if format_name == "technical_joke":
        narration = f"POV: you ask {topic.category} one simple question and get a twelve-page answer. The useful part is this: {summary} So the practical takeaway is to separate the demo from what actually works."
    elif format_name == "fact_explainer":
        narration = f"Here's the simple version: {summary} In plain English, that means it changes how we understand {topic.category.lower()}. The part to remember is what the evidence shows—not the biggest version of the headline."
    elif format_name == "surprising_fact":
        narration = f"The detail most people will miss is this: {summary} That matters because it changes the usual way we think about {topic.category.lower()}. The context is the difference between a real result and hype."
    elif format_name == "timeline":
        narration = f"Here's the short version of how this story developed: {summary} The important point is what changed, not just the headline. That sequence explains why this matters now."
    elif format_name == "question_answer":
        narration = f"The question is simple: what does this actually mean? The answer starts here: {summary} The headline is shorter than the reality, so keep the useful distinction between evidence and interpretation."
    elif format_name == "prediction_watch":
        narration = f"This is a claim worth watching, not a promise: {summary} The next thing to look for is evidence that it holds outside the original context. Until then, separate a measured result from a prediction."
    elif format_name == "reddit_story":
        # Match the reference format: read the post title first, then the
        # author's body. Attribution, permission, and the disclaimer stay in
        # metadata so the narration keeps a direct story rhythm.
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", summary) if part.strip()]
        ending = sentences[-1] if sentences else summary
        body = " ".join(sentences[:-1]).strip()
        narration = f"{source.title}. Here's how it unfolded: {body} Then came the outcome: {ending}" if body else f"{source.title}. {ending}"
    elif format_name == "myth_bust":
        narration = f"This sounds like a bigger claim than it is. Here's what the evidence says: {summary} The honest takeaway is to separate the result from the hype."
    else:
        narration = f"Here's what changed: {summary} Why does it matter? It shifts how we think about {topic.category.lower()}. The key is to follow the evidence, not just the headline."
    disclaimer = "This is educational technology commentary, not professional advice."
    if topic.category == "Finance":
        disclaimer = "This is educational market commentary, not financial advice or an investment recommendation."
    attribution = ""
    if source.author and source.community and source.url.lower().startswith(("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/")):
        attribution = f"\nReddit attribution: u/{source.author} in r/{source.community}"
    description = f"{narration}\n\nSource: {source.url}{attribution}\n{disclaimer}"
    tags = [topic.category, "technology", "science", "explained", "shorts"]
    if topic.category == "Finance":
        tags.extend(["markets", "business"])
    return ScriptPackage(
        hook, narration, title, description, tags, [source.url], format_name,
        topic.category, max(0, variant),
        card_text=(f"{source.title}\n{summary}" if format_name == "reddit_story" else ""),
    )


def normalize_package(topic: Topic, data: dict) -> ScriptPackage:
    """Validate model output before it reaches TTS, rendering, or publishing."""
    source = topic.sources[0]
    required = ("hook", "narration", "title", "description")
    if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required):
        raise ValueError("model output is missing required text fields")
    narration = " ".join(data["narration"].split())[:900].rsplit(" ", 1)[0]
    if len(narration.split()) < 12:
        raise ValueError("model narration is too short")
    format_name = data.get("format_name", "news_breakdown")
    if format_name not in eligible_formats(topic):
        raise ValueError(f"unsupported format: {format_name!r}")
    if format_name == "reddit_story":
        # Keep model-generated Reddit treatments source-faithful: exact title,
        # then the original body. The fallback adds the narrative transitions.
        body = " ".join(source.summary.split())
        narration = f"{source.title}. {body}"[:900].rsplit(" ", 1)[0]
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        raise ValueError("model tags must be a list")
    tags = [str(tag).strip()[:30] for tag in tags if str(tag).strip()][:12]
    description = data["description"].strip()
    if source.url not in description:
        description += f"\n\nSource: {source.url}"
    if source.author and source.community and source.url.lower().startswith(("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/")):
        attribution = f"Reddit attribution: u/{source.author} in r/{source.community}"
        if attribution not in description:
            description += f"\n{attribution}"
    return ScriptPackage(
        data["hook"].strip()[:140],
        narration,
        data["title"].strip()[:100],
        description,
        tags,
        [source.url],
        format_name,
        topic.category,
        card_text=(f"{source.title}\n{source.summary}" if format_name == "reddit_story" else ""),
    )
