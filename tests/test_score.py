import unittest

from app.scoring import duration_ms_from_payload, match_offset_ms, match_score_and_duration


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

    def test_match_offset_from_seconds(self):
        raw = {"matches": [{"offset": 109.620734375, "length": 279000}], "track": {"title": "T"}}
        self.assertEqual(match_offset_ms(raw), 109620)

    def test_duration_from_track_about_attributes(self):
        raw = {
            "title": "Hand in Hand",
            "attributes": {"durationInMillis": 262000},
        }
        self.assertEqual(duration_ms_from_payload(raw), 262000)

    def test_duration_from_section_metadata(self):
        raw = {
            "sections": [
                {
                    "type": "SONG",
                    "metadata": [{"title": "Duration", "text": "4:22"}],
                }
            ]
        }
        self.assertEqual(duration_ms_from_payload(raw), 262000)

    def test_duration_from_track_about_nested_track(self):
        raw = {"track": {"length": 354000, "title": "T"}}
        self.assertEqual(duration_ms_from_payload(raw), 354000)


if __name__ == "__main__":
    unittest.main()
