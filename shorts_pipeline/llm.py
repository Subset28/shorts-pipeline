from __future__ import annotations

import json

import httpx

from .models import ScriptPackage, Topic
from .seo import fallback_package, normalize_package


def create_package(topic: Topic, api_key: str, model: str) -> ScriptPackage:
    """Use OpenAI only when an API key is explicitly configured.

    ChatGPT Plus login/OAuth is not an API credential; the free path remains
    deterministic and source-backed when no API key is available.
    """
    if not api_key:
        return fallback_package(topic)
    source = topic.sources[0]
    prompt = {
        "topic": topic.title,
        "category": topic.category,
        "source_title": source.title,
        "source_summary": source.summary,
        "source_url": source.url,
        "requirements": "Return JSON with hook, narration, title, description, tags, and format_name. Use one format_name from news_breakdown, fact_explainer, myth_bust, technical_joke. Be accurate, original, entertaining, educational, and do not give financial or cyber instructions.",
    }
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "temperature": 0.4, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "You write concise source-backed vertical video scripts."}, {"role": "user", "content": json.dumps(prompt)}]},
            timeout=60,
        )
        response.raise_for_status()
        data = json.loads(response.json()["choices"][0]["message"]["content"])
        return normalize_package(topic, data)
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"LLM unavailable; using source-backed fallback: {exc}")
        return fallback_package(topic)
