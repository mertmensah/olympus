# Olympus

A platform to help people create a digital 3D likeness from personal media.

## Vision

Olympus enables users to upload photos, short videos, and voice clips, then generates a viewable 3D avatar-like reconstruction based on their real-world likeness.

## Current Build State

- Frontend application scaffold (React + Vite)
- Backend API scaffold (FastAPI)
- SQLite-backed job persistence and status endpoints
- Tokenized upload-session contract and direct media upload endpoint
- Supabase Storage integration for media persistence
- Uploaded asset tracking per job
- Background pipeline worker scaffold for staged processing
- Per-stage artifact outputs and quality/reconstruction placeholder metrics
- Initial upload-to-viewer workflow skeleton
- GitHub Pages deployment workflow for frontend

## Repository Structure

- `frontend/`:
	- User experience shell with Home, Upload, and Viewer pages
	- API service client for job flow
- `backend/`:
	- API routes for health checks and job lifecycle
	- SQLite-backed job and artifact persistence
	- Preprocessing stages for image quality and video frame extraction
- `docs/`:
	- Architecture, model strategy, and runbook

## Local Development

Frontend:

1. `cd frontend`
2. `npm install`
3. `npm run dev`

Backend:

1. `cd backend`
2. `python -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r requirements.txt`
5. `uvicorn app.main:app --reload`

## Deployment

Frontend deployment to GitHub Pages is automated using:

- `.github/workflows/pages.yml`

After pushing to `main`, the workflow builds `frontend/dist` and deploys it to Pages.

## Live Project Documents

- See PROJECT_PLAN.md for scope, timeline, and execution roadmap.
- See `docs/ARCHITECTURE.md` for system blueprint.
- See `docs/MODEL_STRATEGY.md` for model integration plan.
- See `docs/RUNBOOK.md` for operational setup.
