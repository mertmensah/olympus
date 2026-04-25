# Getting Started with Olympus

## 30-Second Setup

```bash
git clone https://github.com/mertmensah/olympus.git
cd olympus
cp .env.example .env
# Edit .env with your Supabase credentials (2 lines)
docker-compose up
# Open http://localhost:5173
```

## What You'll See

1. **Home Page**: Welcome to Olympus
2. **Upload Page**: Select a photo (JPG/PNG recommended)
3. **Viewer Page**: Watch the pipeline process, then see interactive 3D reconstruction

## No Supabase Yet?

You need a free Supabase account for media storage:

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up (free)
3. Create a new project
4. Go to Project Settings → API
5. Copy:
   - `Project URL` → `SUPABASE_URL` in `.env`
   - `Service Role Key` (under `anon key`, click "Service role") → `SUPABASE_SECRET_KEY` in `.env`

Here's a visual guide:
```
Supabase Dashboard
├── Project Settings (left sidebar)
├── API tab
├── Project URL: https://XXXXX.supabase.co
└── Service Role Key: eyJ0eXAi... (copy this one)
```

## Troubleshooting

**"Cannot connect to Supabase"**
- Verify `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are correct
- Restart: `docker-compose down && docker-compose up`

**"Port 8000 already in use"**
- Change in `docker-compose.yml`: `"9000:8000"` instead of `"8000:8000"`
- Then access API at `http://localhost:9000`

**"Port 5173 already in use"**
- Same approach with `"5174:5173"` 
- Then access frontend at `http://localhost:5174`

**Upload succeeds but 3D model doesn't appear**
- Check browser console (F12) for errors
- Verify Supabase storage is working: check project dashboard

## Next Steps

### Try Different Modes

**Instant mock generation** (default):
```bash
OLYMPUS_RECONSTRUCT_ADAPTER=mock_v1 docker-compose up
```
No API calls, procedural mesh. Great for testing UI.

**Real 3D reconstruction** (requires Hugging Face):
Get a free token from [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
```bash
OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1 \
OLYMPUS_HF_API_URL=https://api-inference.huggingface.co/models/stabilityai/stable-fast-3d \
OLYMPUS_HF_API_TOKEN=hf_your_token_here \
docker-compose up
```

**Smart routing** (quality-based):
```bash
OLYMPUS_MODEL_SELECTION_STRATEGY=quality_based \
OLYMPUS_QUALITY_THRESHOLD=0.75 \
OLYMPUS_HIGH_QUALITY_ADAPTER=hf_api_v1 \
OLYMPUS_LOW_QUALITY_ADAPTER=mock_v1 \
docker-compose up
```
Only calls expensive API when input quality is good.

## File Structure

```
olympus/
├── frontend/               # React app (http://localhost:5173)
├── backend/                # FastAPI (http://localhost:8000)
├── docs/                   # Detailed guides
├── docker-compose.yml      # Full stack in one command
├── .env.example            # Configuration template
└── README.md               # Full documentation
```

## Understanding the Pipeline

When you upload and generate:

```
1. Upload (JPG → Supabase Storage)
   ↓
2. Ingest Stage (catalog assets)
   ↓
3. Quality Stage (measure brightness/sharpness, extract video frames)
   ↓
4. Reconstruct Stage (generate 3D mesh via mock_v1 or hf_api_v1)
   ↓
5. Postprocess Stage (optimization, prep for delivery)
   ↓
6. Deliver Stage (mark complete, ready for viewing)
   ↓
7. Viewer (interactive Three.js 3D display)
```

You can see artifacts for each stage in the Viewer page.

## Advanced Usage

- **Model Selection**: [docs/MODEL_SELECTION_GUIDE.md](../docs/MODEL_SELECTION_GUIDE.md)
- **HF API Integration**: [docs/HF_API_ADAPTER_GUIDE.md](../docs/HF_API_ADAPTER_GUIDE.md)
- **Docker Deployment**: [docs/DOCKER_DEPLOYMENT.md](../docs/DOCKER_DEPLOYMENT.md)
- **Architecture**: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

## Common Questions

**Q: Can I use it without Docker?**  
A: Yes, see README.md for manual setup (requires Python 3.11+ and ffmpeg).

**Q: How much does this cost?**  
A: Supabase free tier is $0/month. Hugging Face API calls cost money if used beyond free tier.

**Q: Can I deploy to production?**  
A: Yes! See DOCKER_DEPLOYMENT.md for scaling, security, and deployment options.

**Q: What formats does it accept?**  
A: JPG, PNG, MP4, WebM, and other common formats supported by PIL and ffmpeg.

**Q: Is my data private?**  
A: Your media is stored in your own Supabase project. You control all access.

## Support

- 📖 Read the docs: See `docs/` folder
- 🐛 Report bugs: GitHub Issues
- 💬 Ask questions: GitHub Discussions
- 📝 Check logs: `docker-compose logs backend`

## Architecture Highlights

- **Pluggable adapters**: Switch between models without code changes
- **Quality preprocessing**: Automatic image/video analysis
- **Cost optimization**: Route expensive operations strategically
- **A/B testing**: Compare models on production traffic
- **Interactive viewer**: Real-time 3D model display
- **Container-ready**: Deploy anywhere Docker runs

---

**Ready to create some 3D avatars?** 🚀  
Start with: `docker-compose up`
