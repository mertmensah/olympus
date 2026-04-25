# Olympus Runbook

## Local Development

### Frontend

1. `cd frontend`
2. `npm install`
3. `npm run dev`

### Backend

1. `cd backend`
2. `python -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload`

## API Endpoints

- `GET /api/health`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/record`
- `POST /api/jobs/{job_id}/upload-session`
- `PUT /api/uploads/{token}`
- `GET /api/jobs/{job_id}/assets`

## Upload Session Flow

1. Frontend creates job with profile metadata.
2. Frontend sends file descriptors to `POST /api/jobs/{job_id}/upload-session`.
3. API returns tokenized upload targets.
4. Frontend uploads each file directly using `PUT /api/uploads/{token}`.
5. Uploaded assets are tracked via `GET /api/jobs/{job_id}/assets`.

## GitHub Pages Deployment

- Frontend build output is deployed from `frontend/dist`.
- Workflow is in `.github/workflows/pages.yml`.

## Immediate Next Build Step

Implement media upload sessions and persistent job storage.
