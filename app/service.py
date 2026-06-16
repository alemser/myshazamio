import logging
import os
import tempfile
from typing import Optional

from shazamio import Shazam

from app.models import TrackMetadata
from app.scoring import duration_ms_from_payload, match_offset_ms, match_score_and_duration

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

        meta = _parse_track(track, out)
        return await _maybe_fill_duration(meta)
    except Exception as exc:
        logger.exception(
            "shazamio recognition failed filename=%r bytes=%d error=%s: %s",
            filename,
            len(audio_bytes),
            type(exc).__name__,
            exc,
        )
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _safe_suffix(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext in _ALLOWED_EXTENSIONS else ".mp3"





async def _maybe_fill_duration(meta: TrackMetadata) -> TrackMetadata:
    if meta.duration_ms > 0 or not meta.shazam_id:
        return meta
    track_about = getattr(_shazam, "track_about", None)
    if not callable(track_about):
        return meta
    try:
        track_id = int(meta.shazam_id)
    except (TypeError, ValueError):
        return meta
    try:
        about = await track_about(track_id=track_id)
    except Exception:
        logger.warning("track_about failed for shazam_id=%s", meta.shazam_id, exc_info=True)
        return meta
    if not isinstance(about, dict):
        logger.warning("track_about returned non-dict for shazam_id=%s", meta.shazam_id)
        return meta
    dur = duration_ms_from_payload(about)
    if dur <= 0:
        logger.warning("track_about had no duration for shazam_id=%s title=%r", meta.shazam_id, meta.title)
        return meta
    logger.info("duration fallback via track_about shazam_id=%s duration_ms=%d", meta.shazam_id, dur)
    return meta.model_copy(update={"duration_ms": dur})


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

    for section in track.get("sections") or []:
        if not isinstance(section, dict) or section.get("type") != "SONG":
            continue
        for meta in section.get("metadata") or []:
            if not isinstance(meta, dict):
                continue
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
    hub = track.get("hub") if isinstance(track.get("hub"), dict) else {}
    for option in hub.get("options") or []:
        if not isinstance(option, dict):
            continue
        for action in option.get("actions") or []:
            if not isinstance(action, dict):
                continue
            uri = action.get("uri", "")
            if action.get("type") == "uri" and "music.apple.com" in uri:
                apple_music_url = uri
                break
        if apple_music_url:
            break

    images = track.get("images") if isinstance(track.get("images"), dict) else {}
    cover_url = images.get("coverarthq") or images.get("coverart")

    isrc: Optional[str] = track.get("isrc")

    shazam_id_raw = track.get("key")
    shazam_id: Optional[str] = str(shazam_id_raw) if shazam_id_raw not in (None, "") else None
    score, _ = match_score_and_duration(raw)
    duration_ms = duration_ms_from_payload(raw)
    offset_ms = match_offset_ms(raw)

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
        match_offset_ms=offset_ms,
    )
