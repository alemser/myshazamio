import logging
import secrets
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import ErrorResponse, HealthResponse, RecognizeResponse
from app.service import recognize_audio

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

APP_VERSION = "1.1.0"
MAX_FILE_BYTES = settings.max_file_size_mb * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/flac",
    "audio/aac",
    "audio/webm",
    "video/mp4",
    "video/webm",
    "application/octet-stream",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("shazamio service %s starting [env=%s]", APP_VERSION, settings.environment)
    yield
    logger.info("shazamio service stopped")


app = FastAPI(
    title="Shazamio Recognition Service",
    version=APP_VERSION,
    lifespan=lifespan,
    responses={
        401: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


def _verify_api_key(x_api_key: str | None) -> None:
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API key not configured on server")
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health():
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        environment=settings.environment,
    )


@app.post(
    "/recognize",
    response_model=RecognizeResponse,
    responses={
        200: {"description": "Audio recognized or no match found"},
        401: {"description": "Invalid or missing API key"},
        413: {"description": "File too large"},
        422: {"description": "Unsupported media type"},
        500: {"description": "Internal server error"},
    },
    tags=["recognition"],
)
async def recognize(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
):
    _verify_api_key(x_api_key)

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit",
        )

    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported content type: {ct}",
        )

    audio = await file.read(MAX_FILE_BYTES + 1)
    if len(audio) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit",
        )

    logger.info("Recognizing '%s' (%d bytes)", file.filename, len(audio))

    track = await recognize_audio(audio, file.filename or "audio")

    if track is None:
        return RecognizeResponse(success=False, track=None)

    logger.info("Matched: %s - %s", track.title, track.artist)
    return RecognizeResponse(success=True, track=track)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
