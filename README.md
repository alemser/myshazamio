# myshazamio

Audio recognition service built on [ShazamIO](https://github.com/shazamio/ShazamIO) (`shazamio` on PyPI), deployed on Google Cloud Run.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | none | Liveness check |
| `POST` | `/recognize` | `x-api-key` | Recognize audio file |

### POST /recognize

```bash
curl -X POST https://<service-url>/recognize \
  -H "x-api-key: YOUR_API_KEY" \
  -F "file=@song.mp3"
```

**Response (match found):**
```json
{
  "success": true,
  "provider": "shazamio",
  "track": {
    "title": "Bohemian Rhapsody",
    "artist": "Queen",
    "album": "A Night at the Opera",
    "label": "EMI",
    "release_date": "1975",
    "genres": ["Rock"],
    "cover_url": "https://...",
    "shazam_url": "https://www.shazam.com/track/...",
    "apple_music_url": "https://music.apple.com/...",
    "bpm": 144.0,
    "key": "Bb",
    "isrc": "GBUM71029604",
    "shazam_id": "40333609",
    "score": 98,
    "duration_ms": 354000
  }
}
```

**Score semantics (aligned with `oceano-player` shazamio daemon):**

- `matches[0].score` when present: normalized to **0–100** (fractions `0.98` → `98`, values above 100 clamped).
- When `recognize()` returns `track` but **no** `matches[]` (common): **`score` = 100** — identification succeeded; Shazam did not expose fingerprint confidence in the payload.
- `duration_ms` from `matches[0].length` when present, else `0`.

### Track number (album position) — intentionally omitted

**Do not add `track_number` to this service’s `/recognize` response** unless you implement a separate, documented enrichment step. That matches what [ShazamIO](https://github.com/shazamio/ShazamIO) actually returns from `Shazam.recognize()` and what `oceano-player` expects from Shazam-based primaries.

| Concept | ShazamIO / this API | Oceano `track_number` |
|--------|---------------------|------------------------|
| Shazam track id | `track.key` → `shazam_id` | Stored as `shazam_id`; **not** CD/vinyl index |
| Position on release (e.g. `"3"`, `"A2"`) | **Not** in `recognize()` JSON | Filled elsewhere (see below) |

**What `recognize()` gives you** (see `ResponseTrack` / `TrackInfo` in ShazamIO):

- `track.title`, `track.subtitle` (artist), `track.key` (numeric Shazam id)
- `track.sections[]` with `type == "SONG"` and `metadata[]` entries such as **Album**, **Released**, **BPM**, **Key** — there is **no** “Track number” (or equivalent) metadata row in typical recognize payloads
- Optional top-level `matches[]` (fingerprint match metadata: `score`, `length` as ms) — not album tracklist position

**Where ShazamIO *does* expose `trackNumber`:** other APIs and schemas (e.g. `track_about(track_id)`, artist top songs, playlists) use Apple Music–style `trackNumber` / `discNumber` on catalog objects (`AttributesTopSong` in the library). Those are **not** produced by `recognize()` and are a **second HTTP call** per match. This service does not call them today.

**What Oceano does instead** (correct for physical / Now Playing chips):

1. **Discogs** post-recognition: match title against release `tracklist[].position` → `"3"`, `"A2"`, etc.
2. **iTunes / MusicBrainz** catalog apply (user or auto-resolve pick)
3. **Library** `recognition.auto_resolve.infer_track_number`: copy position from another confirmed track on the same album when title/artist match
4. **User** edits via library API

Primary recognizers (embedded `shazamio` daemon, this HTTP wrapper, ACRCloud, AudD) only supply identity + coarse metadata; **`track_number` on the unified state comes from the library row after enrichment**, not from Shazam clip recognition.

**Custom provider mapping:** if your vendor JSON includes a real release index, map it in `oceano-player` field paths — not via inventing it from `shazam_id`. Do **not** map `track.key` or list index to `track_number`.

**oceano-player:** today the Pi stack uses the subprocess daemon in `oceano-player/internal/recognition/shazamio.go`, which emits one JSON line with `shazam_id`, `title`, `artist`, `album`, `score`, and `duration_ms` (no `track_number`). The HTTP `track` object above is a **superset** of that wire shape (same semantics; extra fields for artwork and URLs). When you add a remote “custom provider” client, map `track.shazam_id` → library `shazam_id`, and use `score` / `duration_ms` for `best_score` merge policy parity with the daemon.

**Response (no match):**
```json
{ "success": false, "provider": "shazamio", "track": null }
```

## Local development

```bash
cp .env.example .env
# edit .env and set API_KEY

pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Deploy to Cloud Run

### One-time setup

1. Create an Artifact Registry repository:
   ```bash
   gcloud artifacts repositories create shazamio \
     --repository-format=docker \
     --location=europe-west1
   ```

2. Create a service account and grant roles:
   ```bash
   gcloud iam service-accounts create shazamio-deployer

   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:shazamio-deployer@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:shazamio-deployer@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"

   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:shazamio-deployer@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```

3. Configure [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines) for keyless GitHub Actions auth.

### GitHub secrets required

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GCP_SERVICE_ACCOUNT` | `shazamio-deployer@PROJECT_ID.iam.gserviceaccount.com` |
| `API_KEY` | The API key clients must send |

Push to `main` to trigger a deploy.
