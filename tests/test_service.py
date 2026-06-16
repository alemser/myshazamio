import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules.setdefault("shazamio", MagicMock())

from app.models import TrackMetadata
from app.service import _maybe_fill_duration, recognize_audio


class TestRecognizeAudio(unittest.IsolatedAsyncioTestCase):
    @patch("app.service._recognize_path", new_callable=AsyncMock)
    async def test_shazamio_error_returns_none_not_raise(self, recognize_path):
        recognize_path.side_effect = RuntimeError("Shazam API unavailable")
        out = await recognize_audio(b"\x00" * 100, "capture.wav")
        self.assertIsNone(out)


class TestMaybeFillDuration(unittest.IsolatedAsyncioTestCase):
    async def test_skips_when_duration_present(self):
        meta = TrackMetadata(title="T", shazam_id="123", duration_ms=240000)
        out = await _maybe_fill_duration(meta)
        self.assertEqual(out.duration_ms, 240000)

    async def test_skips_without_shazam_id(self):
        meta = TrackMetadata(title="T", duration_ms=0)
        out = await _maybe_fill_duration(meta)
        self.assertEqual(out.duration_ms, 0)

    @patch("app.service._shazam")
    async def test_fills_from_track_about(self, shazam):
        shazam.track_about = AsyncMock(
            return_value={"attributes": {"durationInMillis": 262000}}
        )
        meta = TrackMetadata(title="Hand in Hand", shazam_id="40333609", duration_ms=0)
        out = await _maybe_fill_duration(meta)
        self.assertEqual(out.duration_ms, 262000)
        shazam.track_about.assert_awaited_once_with(track_id=40333609)


if __name__ == "__main__":
    unittest.main()
