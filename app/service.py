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


async def recognize_audio(audio_bytes: bytes, filename: str = "audio") -> Optional[TrackMetadata]:
    suffix = _safe_suffix(filename)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        out = await _shazam.recognize_song(tmp_path)
        track = out.get("track")
        if not track:
            logger.info("No track match in shazam response")
            return None

        return _parse_track(track)
    except Exception:
        logger.exception("shazamio recognition failed")
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _safe_suffix(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext in _ALLOWED_EXTENSIONS else ".mp3"


def _parse_track(track: dict) -> TrackMetadata:
    genres = []
    primary_genre = track.get("genres", {}).get("primary")
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
    )
