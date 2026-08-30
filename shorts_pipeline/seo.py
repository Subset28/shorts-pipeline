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
    summary = " ".join(source.summary.split())
    if len(summary) > 560:
        summary = summary[:560].rsplit(" ", 1)[0] + "..."
    narration = (
        f"Here is the important part about {topic.title}. {summary} "
        "The practical takeaway is to verify the original source before acting on headlines."
    )
    description = (
        f"{narration}\n\nSource: {source.url}\n"
        "This is educational technology commentary, not professional advice."
    )
    tags = [topic.category, "technology", "science", "explained", "shorts"]
    return ScriptPackage(hook, narration, title, description, tags, [source.url])
