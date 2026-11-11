import tempfile
import unittest
from pathlib import Path
from nexzen.sample_reels import build_sample_batch

class SampleReelTests(unittest.TestCase):
    def test_sample_batch_contains_three_review_only_reels(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_sample_batch(Path(tmp))
            self.assertEqual(len(result["reels"]), 3)
            self.assertFalse(result["publish_eligible"])
            self.assertIn("pending", result["data_quality_note"].lower())
            for item in result["reels"]:
                self.assertTrue((Path(tmp) / item["video"]).is_file())
                self.assertTrue((Path(tmp) / item["slug"] / "storyboard.md").is_file())

if __name__ == "__main__":
    unittest.main()
