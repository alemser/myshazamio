import unittest

from app.service import _match_score_and_duration, _normalize_match_score


class TestNormalizeMatchScore(unittest.TestCase):
    def test_percent(self):
        self.assertEqual(_normalize_match_score(98), 98)

    def test_fraction(self):
        self.assertEqual(_normalize_match_score(0.98), 98)

    def test_clamp_high(self):
        self.assertEqual(_normalize_match_score(150), 100)

    def test_zero(self):
        self.assertEqual(_normalize_match_score(0), 0)


class TestMatchScoreAndDuration(unittest.TestCase):
    def test_with_matches_score(self):
        raw = {"matches": [{"score": 0.92, "length": 240000}], "track": {"title": "T"}}
        score, dur = _match_score_and_duration(raw)
        self.assertEqual(score, 92)
        self.assertEqual(dur, 240000)

    def test_empty_matches_track_present(self):
        raw = {"track": {"title": "Where or When", "subtitle": "Diana Krall"}}
        score, dur = _match_score_and_duration(raw)
        self.assertEqual(score, 100)
        self.assertEqual(dur, 0)

    def test_no_track_no_matches(self):
        raw = {}
        score, dur = _match_score_and_duration(raw)
        self.assertEqual(score, 0)
        self.assertEqual(dur, 0)


if __name__ == "__main__":
    unittest.main()
