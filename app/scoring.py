def match_offset_ms(raw: dict) -> int:
    """Position in the reference track where the capture aligned (ms from start).

    ShazamIO exposes matches[0].offset in seconds (float).
    """
    matches = raw.get("matches") or []
    if not matches:
        return 0
    m0 = matches[0] if isinstance(matches[0], dict) else {}
    off = m0.get("offset")
    if off is None:
        return 0
    try:
        sec = float(off)
    except (TypeError, ValueError):
        return 0
    if sec < 0:
        return 0
    return int(sec * 1000)


def _normalize_duration_value(v) -> int:
    if v is None:
        return 0
    try:
        n = float(v)
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    if n < 1000:
        return int(n * 1000)
    if n > 7_200_000:
        return 0
    return int(n)


def _parse_duration_text(text) -> int:
    if not text or not isinstance(text, str):
        return 0
    text = text.strip()
    if not text:
        return 0
    parts = text.split(":")
    try:
        if len(parts) == 3:
            h, m, s = (float(p) for p in parts)
            return int((h * 3600 + m * 60 + s) * 1000)
        if len(parts) == 2:
            m, s = (float(p) for p in parts)
            return int((m * 60 + s) * 1000)
        if len(parts) == 1:
            return _normalize_duration_value(float(parts[0]))
    except (TypeError, ValueError):
        return 0
    return 0


def _duration_ms_from_object(obj: dict) -> int:
    for key in ("durationInMillis", "duration_ms", "durationMs", "length"):
        ms = _normalize_duration_value(obj.get(key))
        if ms > 0:
            return ms
    attrs = obj.get("attributes")
    if isinstance(attrs, dict):
        ms = _normalize_duration_value(attrs.get("durationInMillis"))
        if ms > 0:
            return ms
    for section in obj.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for meta in section.get("metadata") or []:
            if not isinstance(meta, dict):
                continue
            title = (meta.get("title") or "").strip().lower()
            if title == "duration":
                ms = _parse_duration_text(meta.get("text"))
                if ms > 0:
                    return ms
    return 0


def duration_ms_from_payload(raw: dict) -> int:
    """Best-effort track duration from recognize() or track_about() JSON."""
    if not isinstance(raw, dict):
        return 0
    _, dur = match_score_and_duration(raw)
    if dur > 0:
        return dur
    track = raw.get("track")
    if isinstance(track, dict):
        dur = _duration_ms_from_object(track)
        if dur > 0:
            return dur
    return _duration_ms_from_object(raw)


def match_score_and_duration(raw: dict) -> tuple[int, int]:
    """Extract match score and duration from a raw shazamio response dict.

    matches[0].score is an opaque internal Shazam value, not a 0–1 confidence.
    Shazam is a binary match: track present = identified (100), absent = no match (0).
    """
    duration_ms = 0
    matches = raw.get("matches") or []
    if matches:
        m0 = matches[0] if isinstance(matches[0], dict) else {}
        duration_ms = _normalize_duration_value(m0.get("length"))
    score = 100 if raw.get("track") else 0
    return score, duration_ms
