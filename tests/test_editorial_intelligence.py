import unittest
from nexzen.editorial_intelligence import (
    FULL_MEMBERS, StoryCandidate, normalize_country, score_story, select_stories,
)

def candidate(**overrides):
    raw = dict(
        id="story-1", title="A record-breaking innings", country="India",
        pillar="records", event_type="record", summary="A sourced milestone with historical context.",
        source_url="https://example.com/story", source_name="Official source",
        significance=5, audience_interest=5, analytical_value=4, freshness=5,
        evidence_quality=5, unique_angle=True, match_has_story=False,
        competition="ICC event",
    )
    raw.update(overrides)
    return StoryCandidate(**raw)

class EditorialIntelligenceTests(unittest.TestCase):
    def test_full_member_coverage_has_all_twelve_members(self):
        self.assertEqual(len(FULL_MEMBERS), 12)
        self.assertIn("Ireland", FULL_MEMBERS)
        self.assertEqual(normalize_country("WI"), "West Indies")

    def test_ordinary_match_without_story_is_rejected(self):
        result = score_story(candidate(pillar="analyst", event_type="ordinary_match"))
        self.assertFalse(result["selected"])
        self.assertTrue(any("Ordinary match" in reason for reason in result["reasons"]))

    def test_ordinary_match_with_distinct_story_can_be_considered(self):
        result = score_story(candidate(pillar="analyst", event_type="ordinary_match", match_has_story=True))
        self.assertTrue(result["selected"])

    def test_weak_evidence_is_rejected_even_with_high_interest(self):
        result = score_story(candidate(evidence_quality=2))
        self.assertFalse(result["selected"])

    def test_out_of_range_score_is_rejected(self):
        result = score_story(candidate(significance=6))
        self.assertFalse(result["selected"])

    def test_non_full_member_is_rejected(self):
        result = score_story(candidate(country="Nepal"))
        self.assertFalse(result["selected"])

    def test_selector_ranks_and_limits_stories(self):
        items = [
            candidate(id="low", title="Low interest", significance=1, audience_interest=2,
                      analytical_value=2, freshness=3, evidence_quality=4, competition=""),
            candidate(id="high-a", title="Big milestone"),
            candidate(id="high-b", title="Major squad announcement", pillar="squads",
                      event_type="squad_announcement", significance=5, audience_interest=5,
                      analytical_value=4, freshness=5, evidence_quality=5),
        ]
        result = select_stories(items, limit=2)
        self.assertEqual(len(result["selected"]), 2)
        self.assertEqual(result["selected"][0]["candidate"]["id"], "high-a")

if __name__ == "__main__":
    unittest.main()
