import logging
import os
import tempfile
from typing import Optional

from shazamio import Shazam

from app.models import TrackMetadata

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".mp4", ".webm"}

# Module-level Shazam instance (connection pooling handled internally)
_shazam = Shazam()


async def _recognize_path(path: str) -> dict:
    """Prefer ``recognize`` (same as oceano-player daemon); fall back for older shazamio."""
    recognize = getattr(_shazam, "recognize", None)
    if callable(recognize):
        return await recognize(path)
    return await _shazam.recognize_song(path)


async def recognize_audio(audio_bytes: bytes, filename: str = "audio") -> Optional[TrackMetadata]:
    suffix = _safe_suffix(filename)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        out = await _recognize_path(tmp_path)
        track = out.get("track")
        if not track:
            logger.info("No track match in shazam response")
            return None

        title = (track.get("title") or "").strip()
        artist = (track.get("subtitle") or "").strip()
        if not title and not artist:
            logger.info("Shazam track object present but title and artist empty")
            return None

        return _parse_track(track, out)
    except Exception:
        logger.exception("shazamio recognition failed")
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _safe_suffix(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext in _ALLOWED_EXTENSIONS else ".mp3"


def _normalize_match_score(raw) -> int:
    """Map Shazam matches[0].score to 0–100 (same rules as oceano-player shazamio daemon)."""
    if raw is None:
        return 0
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0
    if v <= 0:
        return 0
    if v <= 1:
        return min(100, int(round(v * 100)))
    if v > 100:
        return 100
    return int(round(v))


def _match_score_and_duration(raw: dict) -> tuple[int, int]:
    score = 0
    duration_ms = 0
    matches = raw.get("matches") or []
    if matches:
        m0 = matches[0] if isinstance(matches[0], dict) else {}
        score = _normalize_match_score(m0.get("score"))
        try:
            duration_ms = int(m0.get("length") or 0)
        except (TypeError, ValueError):
            duration_ms = 0
    elif raw.get("track"):
        # recognize() often omits matches[] even on success; parity with oceano-player daemon.
        score = 100
    return score, duration_ms


def _parse_track(track: dict, raw: dict) -> TrackMetadata:
    genres = []
    genres_obj = track.get("genres")
    primary_genre = genres_obj.get("primary") if isinstance(genres_obj, dict) else None
    if primary_genre:
        genres.append(primary_genre)

    bpm: Optional[float] = None
    key: Optional[str] = None
    album: Optional[str] = None
    release_date: Optional[str] = None

    for section in track.get("sections", []):
        if section.get("type") != "SONG":
            continue
        for meta in section.get("metadata", []):
            title = meta.get("title", "")
            text = meta.get("text")
            if title == "BPM" and text:
                try:
                    bpm = float(text)
                except ValueError:
                    pass
            elif title == "Key" and text:
                key = text
            elif title == "Album" and text:
                album = text
            elif title == "Released" and text:
                release_date = text

    apple_music_url: Optional[str] = None
    for option in track.get("hub", {}).get("options", []):
        for action in option.get("actions", []):
            uri = action.get("uri", "")
            if action.get("type") == "uri" and "music.apple.com" in uri:
                apple_music_url = uri
                break
        if apple_music_url:
            break

    images = track.get("images", {})
    cover_url = images.get("coverarthq") or images.get("coverart")

    isrc: Optional[str] = track.get("isrc")

    shazam_id_raw = track.get("key")
    shazam_id: Optional[str] = str(shazam_id_raw) if shazam_id_raw not in (None, "") else None
    score, duration_ms = _match_score_and_duration(raw)

    return TrackMetadata(
        title=track.get("title"),
        artist=track.get("subtitle"),
        album=album,
        label=track.get("label"),
        release_date=release_date,
        genres=genres,
        cover_url=cover_url,
        shazam_url=track.get("url"),
        apple_music_url=apple_music_url,
        bpm=bpm,
        key=key,
        isrc=isrc,
        shazam_id=shazam_id,
        score=score,
        duration_ms=duration_ms,
    )
