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


def match_score_and_duration(raw: dict) -> tuple[int, int]:
    """Extract match score and duration from a raw shazamio response dict.

    matches[0].score is an opaque internal Shazam value, not a 0–1 confidence.
    Shazam is a binary match: track present = identified (100), absent = no match (0).
    """
    duration_ms = 0
    matches = raw.get("matches") or []
    if matches:
        m0 = matches[0] if isinstance(matches[0], dict) else {}
        try:
            duration_ms = int(m0.get("length") or 0)
        except (TypeError, ValueError):
            duration_ms = 0
    score = 100 if raw.get("track") else 0
    return score, duration_ms
