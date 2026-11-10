"""Typed content models for source-backed cricket editorial assets."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

PILLARS = ("stats", "squads", "records", "battles", "analyst")

@dataclass
class Source:
    name: str
    url: str
    published_at: str = ""
    retrieved_at: str = ""

@dataclass
class Claim:
    text: str
    source_ids: tuple[str, ...] = ()
    context: str = ""

@dataclass
class ContentBrief:
    pillar: str
    title: str
    hook: str
    context: str
    analysis: str
    takeaway: str
    cta: str
    claims: list[Claim] = field(default_factory=list)
    sources: dict[str, Source] = field(default_factory=dict)
    format: str = "T20"
    competition: str = ""
    as_of: str = ""
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ContentBrief":
        claims = [Claim(str(c.get("text", "")), tuple(c.get("source_ids", [])), str(c.get("context", ""))) for c in raw.get("claims", [])]
        sources = {key: Source(**value) for key, value in raw.get("sources", {}).items()}
        names = ("pillar", "title", "hook", "context", "analysis", "takeaway", "cta", "format", "competition", "as_of", "status")
        fields = {key: raw.get(key, "") for key in names}
        fields.update(claims=claims, sources=sources, metadata=raw.get("metadata", {}))
        return cls(**fields)

    def to_dict(self):
        return asdict(self)
