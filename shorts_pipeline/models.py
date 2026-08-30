from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    title: str
    url: str
    summary: str
    published: str = ""


@dataclass(frozen=True)
class Topic:
    title: str
    category: str
    sources: tuple[Source, ...]
    score: float = 0.0


@dataclass
class ScriptPackage:
    hook: str
    narration: str
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    format_name: str = "explainer"
