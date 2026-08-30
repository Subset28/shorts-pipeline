from .models import ScriptPackage, Topic


def fallback_package(topic: Topic) -> ScriptPackage:
    source = topic.sources[0]
    title = topic.title[:85]
    narration = (
        f"Here is the important part about {topic.title}. {source.summary} "
        "The practical takeaway is to verify the original source before acting on headlines."
    )
    description = (
        f"{narration}\n\nSource: {source.url}\n"
        "This is educational technology commentary, not professional advice."
    )
    tags = [topic.category, "technology", "science", "explained", "shorts"]
    return ScriptPackage(topic.title, narration, title, description, tags, [source.url])
