import hashlib

from .models import ScriptPackage, Topic

ALLOWED_FORMATS = ("news_breakdown", "fact_explainer", "myth_bust", "technical_joke")


def fallback_package(topic: Topic, variant: int = 0) -> ScriptPackage:
    source = topic.sources[0]
    title = topic.title[:85]
    format_index = (int(hashlib.sha256(source.url.encode("utf-8")).hexdigest()[:2], 16) + max(0, variant)) % len(ALLOWED_FORMATS)
    format_name = ALLOWED_FORMATS[format_index]
    hooks = {
        "AI": (
            "Can AI explain a prediction without leaking the answer?",
            "The AI concept hiding in this headline",
            "This AI claim needs a closer look",
            "POV: you ask an AI model for one simple answer",
        ),
        "ML": (
            "The hidden risk in machine-learning explanations",
            "Machine learning in plain English",
            "This machine-learning claim needs a closer look",
            "POV: your model is confident for the wrong reason",
        ),
        "Aerospace": (
            "A new space discovery is closer than it looks",
            "The space idea hiding in this headline",
            "The space headline is not the whole story",
            "POV: the spacecraft sends back one more surprise",
        ),
        "Cyber": (
            "This security flaw could affect millions",
            "The security concept in plain English",
            "The security detail hiding in the headline",
            "POV: the bug report arrives five minutes before launch",
        ),
        "Finance": (
            "The market story hiding behind the tech headline",
            "The finance concept in plain English",
            "This market claim needs a closer look",
            "POV: the spreadsheet discovers a bug in your thesis",
        ),
    }
    category_hooks = hooks.get(topic.category)
    hook = category_hooks[format_index] if category_hooks else f"The {format_name.replace('_', ' ')} behind {topic.category.lower()}"
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
    if format_name not in ALLOWED_FORMATS:
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
