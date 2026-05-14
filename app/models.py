from pydantic import BaseModel
from typing import Optional, List


class TrackMetadata(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    label: Optional[str] = None
    release_date: Optional[str] = None
    genres: List[str] = []
    cover_url: Optional[str] = None
    shazam_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    isrc: Optional[str] = None


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
