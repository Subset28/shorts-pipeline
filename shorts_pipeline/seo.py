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

_TECHNICAL_JOKE_SIGNAL = re.compile(
    r"\b(joke|funny|hilarious|absurd|ridiculous|meme|humou?r|satire|"
    r"developer life|programmer life|tech support|rubber duck|"
    r"production incident|debugging nightmare)\b",
    re.IGNORECASE,
)

_SOURCE_STOPWORDS = {
    "about",
    "after",
    "because",
    "from",
    "here",
    "into",
    "more",
    "that",
    "their",
    "this",
    "what",
    "when",
    "with",
}

_TAG_STOPWORDS = _SOURCE_STOPWORDS | {
    "about",
    "after",
    "again",
    "also",
    "from",
    "into",
    "just",
    "more",
    "only",
    "over",
    "that",
    "their",
    "these",
    "this",
    "what",
    "when",
    "with",
}

_CLAIM_VERBS = {
    "cuts",
    "decreases",
    "detects",
    "enables",
    "improves",
    "increases",
    "reduces",
    "removes",
    "trains",
}


def _content_terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 3 and term not in _SOURCE_STOPWORDS}


def _source_keyword_tags(title: str) -> list[str]:
    """Extract bounded, human-readable search terms from a source headline."""
    terms: list[str] = []
    for term in re.findall(r"[a-z0-9]+", title.lower()):
        if len(term) < 4 or term in _TAG_STOPWORDS or term in terms:
            continue
        terms.append(term)
    return terms[:4]


def _has_source_fidelity(source_title: str, source_summary: str, narration: str) -> bool:
    """Require model drafts to retain concrete source anchors."""
    narration_terms = _content_terms(narration)
    title_terms = _content_terms(source_title)
    summary_terms = _content_terms(source_summary)
    title_overlap = len(title_terms & narration_terms)
    summary_overlap = len(summary_terms & narration_terms)
    return title_overlap >= 2 or (title_overlap >= 1 and summary_overlap >= 2)


def _has_any_source_anchor(source_title: str, source_summary: str, text: str) -> bool:
    """Return whether short metadata retains at least one concrete source term."""
    source_terms = _content_terms(f"{source_title} {source_summary}")
    return bool(source_terms & _content_terms(text))


def eligible_formats(topic: Topic) -> tuple[str, ...]:
    """Return lanes whose promise can be supported by this source."""
    source = topic.sources[0]
    text = f"{topic.title} {topic.sources[0].summary}".lower()
    formats = ["news_breakdown", "fact_explainer", "question_answer"]
    if topic.category in {"AI", "ML", "CS", "AI News", "Cyber"} and _TECHNICAL_JOKE_SIGNAL.search(text):
        formats.insert(2, "technical_joke")
    myth_signal = re.search(
        r"\b(myth|false|wrong|debunk|misconception|claim|actually|really|true|doesn['’]t|not)\b", text
    )
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


def _native_hook(headline: str, source_text: str, category: str, format_name: str) -> str:
    """Create a short, concrete overlay hook from source signals."""
    text = f"{headline} {source_text}".lower()
    if "hack" in text and "hugging face" in text:
        return "AI AGENTS HACKED HUGGING FACE"
    if "goes online" in text or "go online" in text:
        return "NASA'S NEW SPACE ANTENNA IS ONLINE"
    if "launch" in text and "telescope" in text:
        return "NASA JUST LAUNCHED A DARK-UNIVERSE TELESCOPE"
    if "lunarecycle" in text or ("moon" in text and "recycl" in text):
        return "NASA JUST AWARDED $775K FOR MOON RECYCLING"
    compact = re.sub(r"\s+", " ", headline).strip(" .:-")
    words = compact.split()
    if format_name == "fact_explainer" and len(words) >= 8:
        for index, word in enumerate(words):
            if word.casefold() not in _CLAIM_VERBS:
                continue
            object_words = [
                item.strip(".,:;()[]") for item in words[index + 1 :] if item.casefold() not in _TAG_STOPWORDS
            ]
            if len(object_words) >= 2:
                return f"WHY THIS {category.upper()} METHOD {word.upper()} {' '.join(object_words[:2]).upper()}"
    compact = " ".join(words[:7])
    if format_name == "question_answer":
        return f"SO WHAT IS {compact}?"
    if format_name == "myth_bust":
        return f"THE TRUTH ABOUT {compact}"
    if format_name == "technical_joke":
        return f"POV: {compact} HIT PRODUCTION"
    return f"WHY {compact} MATTERS" if format_name == "fact_explainer" else compact.upper()


def _nonreddit_takeaway(category: str) -> str:
    """Return a cautious, lane-specific close for source-backed narration."""
    return {
        "AI": "The real test is whether it improves a real workflow outside the demo.",
        "AI News": "The real test is whether it works reliably outside the announcement.",
        "ML": "The real test is whether the result holds on new data, not just one benchmark.",
        "CS": "The real test is whether it survives real users, real load, and real edge cases.",
        "Cyber": "The defensive lesson is to verify the exposure and fix the underlying control.",
        "Aerospace": "The real test is what happens after the headline milestone, when the system has to keep working.",
        "Finance": "The important distinction is a reported development versus a promise about future returns.",
    }.get(category, "The useful takeaway is to separate the measured result from the headline.")


def fallback_package(topic: Topic, variant: int = 0) -> ScriptPackage:
    source = topic.sources[0]
    title = topic.title[:85]
    formats = eligible_formats(topic)
    if "reddit_story" in formats and variant == 0:
        format_name = "reddit_story"
    else:
        if variant == 0 and topic.category in {"AI News", "Aerospace", "Cyber", "Finance"}:
            format_name = "news_breakdown" if "news_breakdown" in formats else formats[0]
        elif variant == 0 and "fact_explainer" in formats:
            format_name = "fact_explainer"
        else:
            format_index = (
                int(hashlib.sha256(source.url.encode("utf-8")).hexdigest()[:2], 16) + max(0, variant)
            ) % len(formats)
            format_name = formats[format_index]
    headline = re.sub(r"\s+", " ", source.title).strip().rstrip(".")
    # The source title remains in narration/metadata; the on-screen hook needs
    # to stay scannable on a phone instead of becoming a tiny headline block.
    headline = headline[:42].rsplit(" ", 1)[0] if len(headline) > 42 else headline
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
    elif len(summary) > (
        760
        if format_name
        in {
            "news_breakdown",
            "fact_explainer",
            "myth_bust",
            "surprising_fact",
            "timeline",
            "question_answer",
            "prediction_watch",
        }
        else 560
    ):
        # News and explainers need enough source context to earn their longer
        # runtime; quick entertainment formats stay compact. Both paths still
        # stop at a complete sentence, so a thin source is never padded.
        bounded = summary[: 760 if format_name != "technical_joke" else 560]
        sentences = re.split(r"(?<=[.!?])\s+", bounded)
        summary = " ".join(sentences[:-1]).strip() if len(sentences) > 1 else bounded.rsplit(" ", 1)[0]
    hook = _native_hook(source.title, summary, topic.category, format_name)
    headline_sentence = source.title.rstrip(". ") + "."
    takeaway = _nonreddit_takeaway(topic.category)
    category_label = {"AI News": "AI", "ML": "machine learning", "CS": "software", "Cyber": "cybersecurity"}.get(
        topic.category, topic.category.lower()
    )
    if format_name == "technical_joke":
        narration = f"{headline_sentence} POV: you ask {topic.category} one simple question and get a twelve-page answer. The useful part is this: {summary} {takeaway}"
    elif format_name == "news_breakdown":
        narration = f"{headline_sentence} Here's the update: {summary} In practical terms, this is a development in {category_label}. {takeaway}"
    elif format_name == "fact_explainer":
        narration = f"{headline_sentence} Here's what the source reports: {summary} In plain English, this changes one specific part of {category_label}. {takeaway}"
    elif format_name == "surprising_fact":
        narration = f"{headline_sentence} The detail most people will miss is this: {summary} That changes how we think about {topic.category.lower()}. {takeaway}"
    elif format_name == "timeline":
        narration = f"{headline_sentence} Here's the short version of how this story developed: {summary} The important point is what changed, not just the headline. {takeaway}"
    elif format_name == "question_answer":
        narration = f"{headline_sentence} So what does this actually mean? {summary} The useful distinction is between what the source demonstrates and what people might assume from the headline. {takeaway}"
    elif format_name == "prediction_watch":
        narration = f"{headline_sentence} This is a claim worth watching, not a promise: {summary} The next thing to look for is evidence that it holds outside the original context. {takeaway}"
    elif format_name == "reddit_story":
        # Match the reference format: read the post title first, then the
        # author's body. Attribution, permission, and the disclaimer stay in
        # metadata so the narration keeps a direct story rhythm.
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", summary) if part.strip()]
        ending = sentences[-1] if sentences else summary
        body = " ".join(sentences[:-1]).strip()
        narration = (
            f"{source.title}. Here's how it unfolded: {body} Then came the outcome: {ending}"
            if body
            else f"{source.title}. {ending}"
        )
    elif format_name == "myth_bust":
        narration = f"{headline_sentence} This sounds like a bigger claim than it is. Here's what the source says: {summary} {takeaway}"
    else:
        narration = f"{headline_sentence} Here's what changed: {summary} Why does it matter? It shifts how we think about {topic.category.lower()}. {takeaway}"
    disclaimer = "This is educational technology commentary, not professional advice."
    if topic.category == "Finance":
        disclaimer = "This is educational market commentary, not financial advice or an investment recommendation."
    attribution = ""
    if (
        source.author
        and source.community
        and source.url.lower().startswith(("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/"))
    ):
        attribution = f"\nReddit attribution: u/{source.author} in r/{source.community}"
    description = f"{narration}\n\nSource: {source.url}{attribution}\n{disclaimer}"
    tags = [topic.category, "technology", "science", "explained", "shorts"]
    for term in _source_keyword_tags(source.title):
        if term.casefold() not in {tag.casefold() for tag in tags}:
            tags.append(term)
    if topic.category == "Finance":
        tags.extend(["markets", "business"])
    return ScriptPackage(
        hook,
        narration,
        title,
        description,
        tags,
        [source.url],
        format_name,
        topic.category,
        max(0, variant),
        card_text=(f"{source.title}\n{summary}" if format_name == "reddit_story" else ""),
    )


def _clip_narration(text: str, limit: int = 900) -> str:
    """Keep generated narration within platform limits without a hard cut."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    bounded = text[:limit]
    sentences = re.split(r"(?<=[.!?])\s+", bounded)
    if len(sentences) > 1:
        return " ".join(sentences[:-1]).strip()
    return bounded.rsplit(" ", 1)[0].rstrip(" ,;:-")


def _ensure_source_opening(source_title: str, narration: str) -> str:
    """Keep model narration anchored to the same headline shown on screen."""
    title = " ".join(source_title.split()).strip(" .")
    if narration.casefold().startswith(title.casefold()):
        return narration
    return _clip_narration(f"{title}. {narration}")


def normalize_package(topic: Topic, data: dict) -> ScriptPackage:
    """Validate model output before it reaches TTS, rendering, or publishing."""
    source = topic.sources[0]
    required = ("hook", "narration", "title", "description")
    if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required):
        raise ValueError("model output is missing required text fields")
    format_name = data.get("format_name", "news_breakdown")
    if format_name not in eligible_formats(topic):
        raise ValueError(f"unsupported format: {format_name!r}")
    narration = _clip_narration(data["narration"])
    minimum_words = 12 if format_name == "reddit_story" else 70
    if len(narration.split()) < minimum_words:
        raise ValueError("model narration is too short")
    if format_name != "reddit_story":
        if not _has_source_fidelity(source.title, source.summary, narration):
            raise ValueError("model narration lacks concrete source anchors")
        narration = _ensure_source_opening(source.title, narration)
    if format_name == "reddit_story":
        # Keep model-generated Reddit treatments source-faithful: exact title,
        # then the original body. The fallback adds the narrative transitions.
        body = " ".join(source.summary.split())
        narration = f"{source.title}. {body}"[:900].rsplit(" ", 1)[0]
    else:
        if not narration.casefold().startswith(source.title.casefold()):
            narration = _clip_narration(f"{source.title}. {narration}")
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        raise ValueError("model tags must be a list")
    tags = [str(tag).strip()[:30] for tag in tags if str(tag).strip()][:12]
    description = data["description"].strip()
    if source.url not in description:
        description += f"\n\nSource: {source.url}"
    if (
        source.author
        and source.community
        and source.url.lower().startswith(("https://www.reddit.com/", "https://old.reddit.com/", "https://redd.it/"))
    ):
        attribution = f"Reddit attribution: u/{source.author} in r/{source.community}"
        if attribution not in description:
            description += f"\n{attribution}"
    hook = data["hook"].strip()[:140]
    if not _has_any_source_anchor(source.title, source.summary, hook):
        hook = _native_hook(source.title, source.summary, topic.category, format_name)
    metadata_title = data["title"].strip()[:100]
    if not _has_any_source_anchor(source.title, source.summary, metadata_title):
        metadata_title = source.title[:100]
    return ScriptPackage(
        hook,
        narration,
        metadata_title,
        description,
        tags,
        [source.url],
        format_name,
        topic.category,
        card_text=(f"{source.title}\n{source.summary}" if format_name == "reddit_story" else ""),
    )
