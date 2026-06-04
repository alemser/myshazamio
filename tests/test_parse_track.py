import sys
import unittest
from unittest.mock import MagicMock

# service.py imports shazamio at load time; stub it for unit tests.
sys.modules.setdefault("shazamio", MagicMock())

from app.service import _parse_track  # noqa: E402


class TestParseTrack(unittest.TestCase):
    def test_duration_from_sections_when_matches_length_missing(self):
        raw = {
            "track": {
                "title": "Walking By Myself",
                "subtitle": "Gary Moore",
                "key": "20000000",
                "sections": [
                    {
                        "type": "SONG",
                        "metadata": [{"title": "Duration", "text": "2:56"}],
                    }
                ],
            },
            "matches": [{"offset": 9.0}],
        }
        meta = _parse_track(raw["track"], raw)
        self.assertEqual(meta.duration_ms, 176000)
        self.assertEqual(meta.match_offset_ms, 9000)
        self.assertEqual(meta.shazam_id, "20000000")


if __name__ == "__main__":
    unittest.main()
