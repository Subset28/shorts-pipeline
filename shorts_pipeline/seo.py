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
)


def eligible_formats(topic: Topic) -> tuple[str, ...]:
    """Return lanes whose promise can be supported by this source."""
    text = f"{topic.title} {topic.sources[0].summary}".lower()
    formats = ["news_breakdown", "fact_explainer", "myth_bust", "technical_joke", "question_answer"]
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
    return tuple(formats)


def fallback_package(topic: Topic, variant: int = 0) -> ScriptPackage:
    source = topic.sources[0]
    title = topic.title[:85]
    formats = eligible_formats(topic)
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
    }
    hook = hook_templates[format_name].format(headline=headline)
    summary = " ".join(source.summary.split())
    if len(summary.split()) < 8:
        # Some RSS feeds, especially link aggregators, provide only URLs and
        # engagement counts. The title is safer and more intelligible than
        # narrating feed boilerplate or inventing missing context.
        summary = source.title
    if len(summary) > 560:
        summary = summary[:560].rsplit(" ", 1)[0] + "..."
    if format_name == "technical_joke":
        narration = f"POV: you ask {topic.category} to explain itself and it sends you a twelve-page PDF. The useful version is this: {summary} The takeaway is to check the original source before trusting a headline."
    elif format_name == "fact_explainer":
        narration = f"Here is the one-minute version of the idea: {summary} In plain English, that means the result matters because it changes how we understand {topic.category.lower()}. The important caveat is to read the original source before turning a finding into a fact."
    elif format_name == "surprising_fact":
        narration = f"The detail most people will miss is this: {summary} That is surprising because it changes the usual way we think about {topic.category.lower()}. Check the original source for the full context before repeating the claim."
    elif format_name == "timeline":
        narration = f"Here is the short version of how this story develops: {summary} The important point is what changed, not just the headline. For the dates, methods, and full context, use the original source."
    elif format_name == "question_answer":
        narration = f"The question is simple: what does this actually mean? The source says: {summary} The answer is more nuanced than the headline, so treat this as a source-backed explanation—not a guarantee—and check the original report."
    elif format_name == "prediction_watch":
        narration = f"This is a claim worth watching, not a promise: {summary} The next thing to look for is evidence that the result holds outside the original context. Until then, separate a measured result from a prediction."
    elif format_name == "myth_bust":
        narration = f"This sounds like a bigger claim than it is. Here is what the source actually says: {summary} So the honest takeaway is to separate the result from the hype and verify the original source."
    else:
        narration = f"Here is the signal behind the headline: {summary} Why does it matter? It changes how we think about {topic.category.lower()}, but the original source is still the thing to check before repeating the claim."
    disclaimer = "This is educational technology commentary, not professional advice."
    if topic.category == "Finance":
        disclaimer = "This is educational market commentary, not financial advice or an investment recommendation."
    description = f"{narration}\n\nSource: {source.url}\n{disclaimer}"
    tags = [topic.category, "technology", "science", "explained", "shorts"]
    if topic.category == "Finance":
        tags.extend(["markets", "business"])
    return ScriptPackage(hook, narration, title, description, tags, [source.url], format_name, topic.category, max(0, variant))


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
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        raise ValueError("model tags must be a list")
    tags = [str(tag).strip()[:30] for tag in tags if str(tag).strip()][:12]
    description = data["description"].strip()
    if source.url not in description:
        description += f"\n\nSource: {source.url}"
    return ScriptPackage(
        data["hook"].strip()[:140],
        narration,
        data["title"].strip()[:100],
        description,
        tags,
        [source.url],
        format_name,
        topic.category,
    )
