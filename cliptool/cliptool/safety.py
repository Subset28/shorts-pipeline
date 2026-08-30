"""Lightweight safety tagging — not a moderation system, just surfaces
signals already present in platform metadata plus a naive keyword flag
so a downstream human/model can decide."""
from __future__ import annotations

from typing import Dict, List, Optional


def build_safety_notes(
    *,
    age_restricted: Optional[bool],
    title: str,
    transcript_excerpt: Optional[str],
    flagged_keywords: List[str],
) -> List[str]:
    notes: List[str] = []

    if age_restricted is None:
        notes.append("age_restricted: unknown")
    else:
        notes.append(f"age_restricted: {str(age_restricted).lower()}")

    hay = f"{title} {transcript_excerpt or ''}".lower()
    hits = [kw for kw in flagged_keywords if kw.lower() in hay]
    if hits:
        notes.append(f"flagged_terms: {', '.join(sorted(set(hits)))}")
    else:
        notes.append("flagged_terms: none")

    return notes


def rights_notes_for_platform(platform: str) -> Dict[str, Optional[str]]:
    """Returns default license/reuse-risk notes. These are conservative
    defaults, not legal advice — always let a human confirm before
    reuse in monetized content."""
    if platform in ("twitch_clip", "twitch_vod"):
        return {
            "license_or_rights_note": "Creator-owned Twitch content; no implied license to reuse.",
            "reuse_risk_note": "Confirm creator permission/fair-use basis before publishing.",
        }
    if platform == "youtube":
        return {
            "license_or_rights_note": "Standard YouTube license unless creator states otherwise.",
            "reuse_risk_note": "Confirm creator permission/fair-use basis before publishing.",
        }
    return {"license_or_rights_note": None, "reuse_risk_note": None}
