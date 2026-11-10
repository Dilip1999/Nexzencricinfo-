import unittest
from nexzen.generators import GENERATORS, generate_brief
from nexzen.quality import validate_brief

SOURCE = {"scorecard": {"name": "Official scorecard fixture", "url": "https://example.com/scorecard", "published_at": "2026-11-10", "retrieved_at": "2026-11-10"}}
CLAIMS = [{"text": "Test fixture claim; replace with a verified cricket fact.", "source_ids": ["scorecard"]}]

class PillarGeneratorTests(unittest.TestCase):
    def test_all_five_generators_create_their_own_pillar(self):
        for pillar, generator in GENERATORS.items():
            with self.subTest(pillar=pillar):
                brief = generator(title="Fixture title", context="Fixture context", analysis="Evidence-led interpretation.", takeaway="Limited conclusion.", claims=CLAIMS, sources=SOURCE, as_of="2026-11-10")
                self.assertEqual(brief.pillar, pillar)
                self.assertEqual(brief.status, "draft")
                self.assertEqual(brief.claims[0].source_ids, ("scorecard",))
                self.assertTrue(validate_brief(brief).eligible)

    def test_missing_claims_are_rejected(self):
        with self.assertRaises(ValueError):
            generate_brief("stats", title="x", context="x", analysis="x", takeaway="x", claims=[], sources=SOURCE)

    def test_unknown_pillar_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_brief("rumours", title="x", context="x", analysis="x", takeaway="x", claims=CLAIMS, sources=SOURCE)

    def test_source_reference_mismatch_fails_quality_gate(self):
        brief = GENERATORS["records"](title="Fixture", context="Context", analysis="Analysis", takeaway="Takeaway", claims=[{"text":"Claim","source_ids":["missing"]}], sources=SOURCE)
        self.assertFalse(validate_brief(brief).eligible)

if __name__ == "__main__": unittest.main()
