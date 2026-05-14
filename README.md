# myshazamio

Audio recognition service built on [shazamio](https://github.com/dotX12/shazamio), deployed on Google Cloud Run.

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
    "release_date": "1975",
    "genres": ["Rock"],
    "cover_url": "https://...",
    "shazam_url": "https://www.shazam.com/track/...",
    "apple_music_url": "https://music.apple.com/...",
    "bpm": 144.0,
    "key": "Bb",
    "isrc": "GBUM71029604"
  }
}
```

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
