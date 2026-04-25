# Olympus

> **🚀 Live Platform**: https://mertmensah.github.io/olympus  
> Backend API: `http://localhost:8000` (local development)

A platform to help people create a digital 3D likeness from personal media.

## Vision

Olympus enables users to upload photos, short videos, and voice clips, then generates a viewable 3D avatar-like reconstruction based on their real-world likeness.

## Current Build State

- ✅ Frontend application with Home, Upload, and interactive 3D Viewer (React + Vite)
- ✅ Backend API with FastAPI
- ✅ SQLite-backed job persistence and status endpoints
- ✅ Tokenized upload-session contract and direct media upload endpoint
- ✅ Supabase Storage integration for media persistence
- ✅ Uploaded asset tracking per job
- ✅ Background pipeline worker with staged processing
- ✅ Per-stage artifact outputs (ingest, quality, reconstruct, postprocess, deliver)
- ✅ Quality preprocessing (image brightness/sharpness, video frame extraction)
- ✅ Adapter-driven reconstruction with runtime telemetry
- ✅ GLB 3D mesh generation (mock_v1 adapter)
- ✅ Interactive Three.js viewer for 3D reconstructions
- ✅ Advanced model selection (quality-based routing, A/B testing)
- ✅ HF API v1 adapter for remote inference
- ✅ Docker containerization for production deployment
- ✅ GitHub Pages deployment workflow for frontend

## Quick Start (Docker)

### Prerequisites
- Docker and Docker Compose installed
- Supabase project URL and secret key (free tier available)

### Step 1: Setup Environment

```bash
git clone https://github.com/mertmensah/olympus.git
cd olympus
cp .env.example .env
```

### Step 2: Configure .env

Edit `.env` with your Supabase credentials:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key-here
OLYMPUS_RECONSTRUCT_ADAPTER=mock_v1  # Use mock for instant testing
```

### Step 3: Run with Docker Compose

```bash
docker-compose up
```

**That's it!** The platform will be available at:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000/api/health
- API: http://localhost:8000

### Step 4: Test the Platform

1. Open http://localhost:5173 in your browser
2. Click **Upload** and select a photo
3. Click **Start Generation** to process
4. View the interactive 3D model in the **Viewer** tab

---

## Deployment Strategies

### Development (Fast, No API Needed)
```bash
OLYMPUS_RECONSTRUCT_ADAPTER=mock_v1 docker-compose up
```
Generates instant procedural 3D meshes. Perfect for UI/workflow testing.

### Production (Real Inference)
```bash
OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1 \
OLYMPUS_HF_API_URL=https://api-inference.huggingface.co/models/your-model \
OLYMPUS_HF_API_TOKEN=hf_your_token \
docker-compose up
```
Calls remote Hugging Face API for realistic reconstructions. Requires valid credentials.

### Cost-Optimized (Quality-Based Routing)
```bash
OLYMPUS_MODEL_SELECTION_STRATEGY=quality_based \
OLYMPUS_QUALITY_THRESHOLD=0.75 \
OLYMPUS_HIGH_QUALITY_ADAPTER=hf_api_v1 \
OLYMPUS_LOW_QUALITY_ADAPTER=mock_v1 \
docker-compose up
```
Routes expensive API calls only to high-quality inputs, uses fast mock for others.

---

## Repository Structure

- `frontend/`: React + Vite application with Upload and interactive 3D Viewer
- `backend/`: FastAPI with job pipeline, media preprocessing, and adapter system
- `docs/`: Deployment guides, adapter configuration, model selection strategy
- `Dockerfile`: Production container image
- `docker-compose.yml`: Full stack orchestration
- `.env.example`: Configuration template

---

## Advanced Configuration

### Architecture & Design
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design and data flow.

### Model Selection Strategies
See [docs/MODEL_SELECTION_GUIDE.md](docs/MODEL_SELECTION_GUIDE.md) for:
- Quality-based routing (optimize costs)
- A/B testing (compare models)
- Fallback chains (reliability)

### Hugging Face Integration
See [docs/HF_API_ADAPTER_GUIDE.md](docs/HF_API_ADAPTER_GUIDE.md) for remote inference setup.

### Docker Deployment
See [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) for:
- Production deployment
- Health checks & monitoring
- Scaling recommendations
- Troubleshooting

---

## Local Development (Manual)

If you prefer to run backend and frontend separately without Docker:

### Frontend
```bash
cd frontend
npm install
npm run dev
# Available at http://localhost:5173
```

### Backend
```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
# Available at http://localhost:8000
```

Requires: Python 3.11+, ffmpeg system package

---

## Technology Stack

**Backend**: FastAPI, Pydantic, SQLite, Supabase Storage, PIL, ffmpeg, trimesh  
**Frontend**: React 18, Vite, Three.js, OrbitControls  
**DevOps**: Docker, Docker Compose, GitHub Actions  
**Adapters**: mock_v1 (procedural), hf_api_v1 (remote API)

---

## Extending the Platform

### Add a New Adapter

1. Create `backend/app/services/reconstruct_adapters/my_adapter_v1.py`
2. Implement `ReconstructAdapter` interface
3. Register in `registry.py`
4. Configure via `OLYMPUS_PRIMARY_ADAPTER=my_adapter_v1`

See [docs/MODEL_SELECTION_GUIDE.md](docs/MODEL_SELECTION_GUIDE.md#extending-add-a-new-adapter) for details.

---

## Troubleshooting

### Backend won't start
```bash
docker-compose logs backend
```

### Frontend can't reach API
Ensure backend is running: `curl http://localhost:8000/api/health`

### Database errors
Reset: `docker volume rm olympus_backend_data && docker-compose down && docker-compose up`

### Model not loading in viewer
Check browser console for CORS issues. Verify Supabase bucket is accessible.

For more, see [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md#troubleshooting).

---

## Contributing

1. Create a feature branch
2. Test locally with `docker-compose up`
3. Commit with clear messages
4. Push and create a PR

---

## License

MIT

---

## Support & Feedback

- Report issues: https://github.com/mertmensah/olympus/issues
- Documentation: See `/docs` folder
- Questions: Open a discussion or issue

## Deployment

Frontend deployment to GitHub Pages is automated using:

- `.github/workflows/pages.yml`

After pushing to `main`, the workflow builds `frontend/dist` and deploys it to Pages.

## Live Project Documents

- See PROJECT_PLAN.md for scope, timeline, and execution roadmap.
- See `docs/ARCHITECTURE.md` for system blueprint.
- See `docs/MODEL_STRATEGY.md` for model integration plan.
- See `docs/RUNBOOK.md` for operational setup.
