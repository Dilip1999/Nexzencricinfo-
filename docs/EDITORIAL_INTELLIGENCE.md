# Cricket Editorial Intelligence — QA milestone

## Editorial coverage

The primary international coverage is all 12 ICC Full Members:

Afghanistan, Australia, Bangladesh, England, India, Ireland, New Zealand, Pakistan, South Africa, Sri Lanka, West Indies and Zimbabwe.

India, Pakistan, England and Australia receive a small audience-priority bonus. This is a ranking hint, not an exclusion rule: a strong story from any Full Member can outrank a weak story from a priority country.

Franchise and domestic competitions are considered selectively when they create a meaningful story. The configured flagship competition terms include ICC events, IPL, World Cup, Champions Trophy and World Test Championship. This is not an exhaustive league allowlist.

## Selection policy

The engine evaluates each candidate on five dimensions, each scored from 0 to 5:

1. Significance
2. Audience interest
3. Analytical value
4. Freshness
5. Evidence quality

A small bonus may be added for priority countries and flagship competitions. The default selection threshold is 16/25 and the default batch limit is three stories.

Hard exclusions:
- No named HTTPS source and publisher.
- Evidence quality below 3/5.
- Freshness below 2/5.
- Unsupported country or content pillar.
- Duplicate or repetitive angle.
- An ordinary match with no distinct story angle.

A match is not a story by itself. Examples of angles that may qualify include a meaningful record, a major milestone, a decisive tactical pattern, an important squad announcement, a high-interest player matchup, or a major breaking development. The engine ranks supplied candidates; it does not discover facts or independently verify provider claims. Scores should be assigned by upstream rules/editorial review and must not be fabricated.

## Supported pillars

- Stats & Analytics
- Squad Analysis
- Records & Milestones
- Player Battles
- Match Intelligence
- Breaking News (major developments only)

## QA usage

```python
from nexzen.editorial_intelligence import StoryCandidate, select_stories

candidates = [StoryCandidate.from_dict(item) for item in candidate_payload]
result = select_stories(candidates)
for item in result["selected"]:
    print(item["candidate"]["title"], item["evaluation"]["score"])
```

## Release boundary

This milestone is selection logic and tests only. It does not fetch live fixtures, generate or render a Reel, schedule content, call Instagram, or merge to production. All work remains on the QA branch. Every selected story still requires source verification, content quality validation and owner approval.
