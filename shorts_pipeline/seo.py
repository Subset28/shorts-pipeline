import hashlib

from .models import ScriptPackage, Topic


def fallback_package(topic: Topic) -> ScriptPackage:
    source = topic.sources[0]
    title = topic.title[:85]
    hooks = {
        "AI": "Can AI explain a prediction without leaking the answer?",
        "ML": "The hidden risk in machine-learning explanations",
        "Aerospace": "A new space discovery is closer than it looks",
        "Cyber": "This security flaw could affect millions",
    }
    hook = hooks.get(topic.category, f"The part of {topic.category.lower()} nobody is talking about")
    format_index = int(hashlib.sha256(source.url.encode("utf-8")).hexdigest()[:2], 16) % 3
    formats = ("news_breakdown", "myth_bust", "technical_joke")
    format_name = formats[format_index]
    summary = " ".join(source.summary.split())
    if len(summary) > 560:
        summary = summary[:560].rsplit(" ", 1)[0] + "..."
    if format_name == "technical_joke":
        narration = f"POV: you ask {topic.category} to explain itself and it sends you a twelve-page PDF. The useful version is this: {summary} The takeaway is to check the original source before trusting a headline."
    elif format_name == "myth_bust":
        narration = f"This sounds like a bigger claim than it is. Here is what the source actually says: {summary} So the honest takeaway is to separate the result from the hype and verify the original source."
    else:
        narration = f"Here is the signal behind the headline: {summary} Why does it matter? It changes how we think about {topic.category.lower()}, but the original source is still the thing to check before repeating the claim."
    description = (
        f"{narration}\n\nSource: {source.url}\n"
        "This is educational technology commentary, not professional advice."
    )
    tags = [topic.category, "technology", "science", "explained", "shorts"]
    return ScriptPackage(hook, narration, title, description, tags, [source.url], format_name)
