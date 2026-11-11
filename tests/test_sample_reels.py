import json
import tempfile
import unittest
from pathlib import Path
from nexzen.sample_reels import build_sample_batch

class SampleReelTests(unittest.TestCase):
    def test_selected_match_generates_one_review_only_story_reel(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = build_sample_batch(output)
            self.assertEqual(len(result["reels"]), 1)
            self.assertFalse(result["publish_eligible"])
            self.assertEqual(result["status"], "qa_sample_only")
            reel = result["reels"][0]
            self.assertEqual(reel["slug"], "india-nz-kohli-93-story")
            self.assertEqual(reel["scene_count"], 5)
            self.assertTrue((output / reel["video"]).is_file())
            storyboard_path = output / reel["slug"] / "storyboard.md"
            self.assertTrue(storyboard_path.is_file())
            storyboard = storyboard_path.read_text(encoding="utf-8")
            self.assertIn("Virat Kohli", storyboard)
            self.assertIn("**Voiceover:**", storyboard)
            self.assertIn("first-innings context is not shown", storyboard.lower())

if __name__ == "__main__":
    unittest.main()
