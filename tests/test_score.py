import unittest

from app.scoring import match_score_and_duration


class TestMatchScoreAndDuration(unittest.TestCase):
    def test_matches_with_track_gives_100(self):
        # matches[0].score is opaque — track present means identified.
        raw = {"matches": [{"score": 0.000052, "length": 240000}], "track": {"title": "T"}}
        score, dur = match_score_and_duration(raw)
        self.assertEqual(score, 100)
        self.assertEqual(dur, 240000)

    def test_empty_matches_track_present(self):
        raw = {"track": {"title": "Where or When", "subtitle": "Diana Krall"}}
        score, dur = match_score_and_duration(raw)
        self.assertEqual(score, 100)
        self.assertEqual(dur, 0)

    def test_no_track_no_matches(self):
        raw = {}
        score, dur = match_score_and_duration(raw)
        self.assertEqual(score, 0)
        self.assertEqual(dur, 0)

    def test_matches_without_track_gives_0(self):
        raw = {"matches": [{"score": 0.92, "length": 5000}]}
        score, dur = match_score_and_duration(raw)
        self.assertEqual(score, 0)
        self.assertEqual(dur, 5000)

    def test_duration_extracted_from_matches(self):
        raw = {"matches": [{"length": 185000}], "track": {"title": "T"}}
        score, dur = match_score_and_duration(raw)
        self.assertEqual(score, 100)
        self.assertEqual(dur, 185000)


if __name__ == "__main__":
    unittest.main()
