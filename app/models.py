from typing import List, Optional

from pydantic import BaseModel, Field


class TrackMetadata(BaseModel):
    """Fields aligned with oceano-player ``internal/recognition/shazamio.go`` daemon JSON."""

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    label: Optional[str] = None
    release_date: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    cover_url: Optional[str] = None
    shazam_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    isrc: Optional[str] = None
    # Parity with subprocess daemon / ``parseShazamioJSONOutput`` (library id + merge scoring).
    shazam_id: Optional[str] = None
    score: int = 0
    duration_ms: int = 0


class RecognizeResponse(BaseModel):
    success: bool
    provider: str = "shazamio"
    track: Optional[TrackMetadata] = None


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
