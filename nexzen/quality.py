"""Fail-closed editorial provenance and weighted quality checks."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from urllib.parse import urlparse
from .models import ContentBrief, PILLARS

WEIGHTS = {"source_reliability": 30, "relevance": 20, "hook_storytelling": 20, "original_insight": 15, "visual_suitability": 10, "brand_consistency": 5}

@dataclass
class QualityResult:
    score: int
    eligible: bool
    decision: str
    hard_failures: list[str]
    checks: dict[str, bool]
    def to_dict(self):
        return asdict(self)

def validate_brief(brief: ContentBrief) -> QualityResult:
    failures = []
    if brief.pillar not in PILLARS:
        failures.append(f"Unknown pillar: {brief.pillar!r}")
    if not brief.title.strip() or not brief.hook.strip():
        failures.append("A title and hook are required.")
    if not brief.claims:
        failures.append("No factual claims supplied; fail closed until claims are sourced.")
    if not brief.sources:
        failures.append("No sources supplied.")
    for index, claim in enumerate(brief.claims, 1):
        if not claim.text.strip():
            failures.append(f"Claim {index} is empty.")
        if not claim.source_ids:
            failures.append(f"Claim {index} has no source IDs.")
        for source_id in claim.source_ids:
            if source_id not in brief.sources:
                failures.append(f"Claim {index} references missing source {source_id!r}.")
    for source_id, source in brief.sources.items():
        parsed = urlparse(source.url)
        if parsed.scheme != "https" or not parsed.netloc:
            failures.append(f"Source {source_id!r} must have a valid HTTPS URL.")
        if not source.name.strip():
            failures.append(f"Source {source_id!r} is missing a publisher/name.")
    checks = {
        "source_reliability": bool(brief.sources) and all(s.name.strip() and urlparse(s.url).scheme == "https" for s in brief.sources.values()),
        "relevance": brief.pillar in PILLARS and bool(brief.context.strip()),
        "hook_storytelling": bool(brief.hook.strip() and brief.takeaway.strip()),
        "original_insight": bool(brief.analysis.strip()),
        "visual_suitability": bool(brief.title.strip() and brief.metadata.get("visual_concept")),
        "brand_consistency": brief.metadata.get("brand_theme") == "cricket-journal-editorial-luxury",
    }
    score = sum(WEIGHTS[key] for key, passed in checks.items() if passed)
    if failures:
        decision = "REJECT_UNVERIFIED"
    elif score >= 85:
        decision = "ELIGIBLE_FOR_FINAL_REVIEW"
    elif score >= 70:
        decision = "NEEDS_IMPROVEMENT"
    else:
        decision = "REGENERATE"
    return QualityResult(score, not failures and score >= 85, decision, failures, checks)
