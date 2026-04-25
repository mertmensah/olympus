# Olympus Architecture Blueprint

## System Shape

- Frontend SPA on GitHub Pages (React + Vite)
- API service (FastAPI)
- Worker service for AI pipeline execution
- Storage layer for raw media and generated assets
- Metadata database for jobs and profile parameters

## Request Flow

1. Frontend creates generation job via API.
2. API validates payload and persists job record.
3. Worker picks job and executes staged pipeline.
4. Worker writes outputs and updates job stage/status.
5. Frontend polls status and opens viewer once complete.

## Pipeline Stages

- ingest: input manifest and media indexing
- quality: blur/exposure/coverage checks
- reconstruct: core image/video-to-3D inference
- postprocess: cleanup, scale, and export
- deliver: finalize URLs and previews

## Why This Layout

- Keeps frontend static and inexpensive to host.
- Isolates compute-heavy workloads from user-facing UI.
- Allows model stack changes without frontend rewrites.
