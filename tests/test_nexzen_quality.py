import unittest
from nexzen.models import ContentBrief
from nexzen.quality import validate_brief

class QualityGateTests(unittest.TestCase):
    def make_brief(self):
        return ContentBrief.from_dict({
            "pillar":"stats", "title":"Illustrative player analysis", "hook":"What do the numbers show?",
            "context":"Compare a defined competition and format.", "analysis":"Explain the evidence without extrapolating.",
            "takeaway":"The supplied figures support this limited conclusion.", "cta":"Which metric matters most?",
            "as_of":"2026-11-10", "metadata":{"visual_concept":"animated comparison cards", "brand_theme":"cricket-journal-editorial-luxury"},
            "claims":[{"text":"Illustrative claim for unit testing only.","source_ids":["test-source"]}],
            "sources":{"test-source":{"name":"Test fixture publisher","url":"https://example.com/test","published_at":"2026-11-10","retrieved_at":"2026-11-10"}}
        })
    def test_complete_brief_passes_provenance_and_score(self):
        result = validate_brief(self.make_brief())
        self.assertTrue(result.eligible)
        self.assertEqual(result.score, 100)
    def test_missing_source_fails_closed(self):
        brief = self.make_brief()
        brief.sources = {}
        result = validate_brief(brief)
        self.assertFalse(result.eligible)
        self.assertIn("No sources supplied.", result.hard_failures)
    def test_claim_without_source_fails_closed(self):
        brief = self.make_brief()
        brief.claims[0].source_ids = ()
        self.assertFalse(validate_brief(brief).eligible)
    def test_http_source_is_rejected(self):
        brief = self.make_brief()
        brief.sources["test-source"].url = "http://example.com/test"
        self.assertFalse(validate_brief(brief).eligible)
    def test_unknown_pillar_is_rejected(self):
        brief = self.make_brief()
        brief.pillar = "rumours"
        self.assertFalse(validate_brief(brief).eligible)

if __name__ == "__main__":
    unittest.main()
