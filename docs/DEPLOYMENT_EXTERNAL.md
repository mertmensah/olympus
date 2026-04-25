# Deploying Olympus

This guide covers deploying Olympus to public services so anyone can use it.

## Architecture

```
Frontend (React + Vite)
    ↓ (CORS)
Backend (FastAPI) 
    ↓
Supabase Storage + PostgreSQL
```

---

## Option 1: GitHub Pages (Frontend) + Render (Backend)

**Recommended for beginners. Completely free tier available.**

### Step 1: Deploy Backend to Render

1. Go to [https://render.com](https://render.com)
2. Sign up with GitHub
3. Create a new **Web Service**
4. Connect to: `https://github.com/mertmensah/olympus`
5. Settings:
   - Build Command: (leave empty)
   - Start Command: `cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir .`
6. Environment Variables (add all from `.env`):
   - `SUPABASE_URL`
   - `SUPABASE_SECRET_KEY`
   - `OLYMPUS_RECONSTRUCT_ADAPTER`
   - `OLYMPUS_HF_API_URL` (if using hf_api_v1)
   - `OLYMPUS_HF_API_TOKEN` (if using hf_api_v1)
7. Select Plan: **Free** (note: spins down after 15 min inactivity)
8. Click **Create Web Service**
9. Wait for deployment to complete
10. Copy the URL: `https://olympus-xxxx.onrender.com`

### Step 2: Update Frontend to Use Render Backend

Edit `frontend/src/services/api.js`:
```javascript
const API_BASE = "https://olympus-xxxx.onrender.com";  // Use your Render URL
```

**Alternative**: Use environment variable in Vite
```javascript
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

Then create `.env.production`:
```
VITE_API_URL=https://olympus-xxxx.onrender.com
```

### Step 3: Deploy Frontend to GitHub Pages

The workflow is already set up in `.github/workflows/deploy.yml`. It auto-deploys when you push to main.

1. Verify it's enabled: Go to repo Settings → Pages
2. Check "Build and deployment" → Source: GitHub Actions
3. Push any change to trigger deployment:
   ```bash
   git add .
   git commit -m "chore: deploy"
   git push origin main
   ```
4. Frontend will be live at: `https://mertmensah.github.io/olympus`

### Step 4: Test

Open: `https://mertmensah.github.io/olympus`

---

## Option 2: Vercel (Frontend) + Render (Backend)

**Best for Next.js, but works with React too.**

### Deploy Frontend to Vercel

1. Go to [https://vercel.com](https://vercel.com)
2. Click **Add New Project**
3. Import from Git: `https://github.com/mertmensah/olympus`
4. Configure:
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. Environment Variables:
   - `VITE_API_URL`: Your Render backend URL
6. Click **Deploy**

Frontend will be live at: `https://olympus.vercel.app`

Backend: Deploy to Render (same as Option 1)

---

## Option 3: Self-Hosted Docker (Full Control)

**For VPS, DigitalOcean, AWS, Heroku, etc.**

### Prerequisites
- Linux server with Docker installed
- Domain name (optional but recommended)
- SSL certificate (Let's Encrypt, included with some providers)

### Step 1: Prepare Server

```bash
ssh user@your-server.com
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y docker.io docker-compose git
sudo usermod -aG docker $USER
exit
ssh user@your-server.com  # Reconnect to apply docker group
```

### Step 2: Clone and Configure

```bash
git clone https://github.com/mertmensah/olympus.git
cd olympus
cp .env.example .env
nano .env  # Edit with your Supabase credentials
```

### Step 3: Run with Docker Compose

```bash
docker-compose up -d
docker-compose logs -f backend  # Monitor
```

Backend: `http://your-server.com:8000`  
Frontend: `http://your-server.com:5173`

### Step 4: Set Up Nginx Reverse Proxy (Optional)

To run on port 80/443 with a domain:

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
sudo nano /etc/nginx/sites-available/olympus
```

Add:
```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:5173;
}

server {
    listen 80;
    server_name olympus.yourdomain.com;

    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }

    location /api/ {
        proxy_pass http://backend;
    }
}
```

Enable and get SSL:
```bash
sudo ln -s /etc/nginx/sites-available/olympus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d olympus.yourdomain.com
```

Now access: `https://olympus.yourdomain.com`

---

## Deployment Comparison

| Platform | Frontend | Backend | Cost | Effort | Best For |
|----------|----------|---------|------|--------|----------|
| GitHub Pages + Render | ✅ Free | ✅ Free | ~$0/mo* | Low | Getting started |
| Vercel + Render | ✅ Free | ✅ Free | ~$0/mo* | Low | Modern stack |
| Heroku | ❌ (paid only) | ✅ ~$7/mo | ~$7/mo | Medium | Production |
| Self-hosted VPS | ✅ Free | ✅ Free | ~$5-20/mo | High | Full control |
| AWS/GCP | ✅ Free tier | ✅ Free tier | Variable | High | Scaling |

*Free tier has limitations (Render spins down after 15 min inactivity, GitHub Pages on free plan is public)

---

## Environment Variables for Production

| Variable | Example | Required |
|----------|---------|----------|
| `SUPABASE_URL` | `https://xxx.supabase.co` | ✅ Yes |
| `SUPABASE_SECRET_KEY` | `eyJ0eXAi...` | ✅ Yes |
| `OLYMPUS_RECONSTRUCT_ADAPTER` | `mock_v1` | Optional (default) |
| `OLYMPUS_HF_API_URL` | `https://api-inference.huggingface.co/...` | If using hf_api_v1 |
| `OLYMPUS_HF_API_TOKEN` | `hf_xxxx` | If using hf_api_v1 |
| `OLYMPUS_MODEL_SELECTION_STRATEGY` | `quality_based` | Optional |
| `OLYMPUS_UPLOAD_TOKEN_SECRET` | Generate random string | Recommended |

Generate a secure token:
```bash
openssl rand -base64 32
```

---

## Monitoring & Maintenance

### Check Backend Health

```bash
curl https://your-backend-url/api/health
# Response: {"status": "ok"}
```

### View Logs

**Render**: Dashboard → Logs  
**Docker**: `docker-compose logs -f backend`  
**Vercel**: Dashboard → deployments → logs

### Database Access

Olympus uses SQLite (file-based). For self-hosted:
```bash
# Inside container
docker-compose exec backend sqlite3 /app/data/olympus.db ".tables"
```

For production scale, migrate to PostgreSQL (use Supabase's built-in Postgres).

---

## Performance Tips

1. **Cache frontend assets**: Render/Vercel do this automatically
2. **Use quality-based routing**: Only call expensive APIs for good inputs
3. **Monitor Supabase usage**: Free tier has limits
4. **Keep Render warm**: Use a monitoring service to ping `/api/health` every 10 minutes
5. **Enable HTTP compression**: Nginx/reverse proxies do this automatically

---

## Troubleshooting Deployments

**"CORS error in browser console"**
- Backend URL might be wrong
- Check: `fetch('https://your-backend/api/health')`
- Add `Access-Control-Allow-Origin` headers if needed

**"Cannot reach backend"**
- Verify backend is running: `curl https://your-backend/api/health`
- Check environment variables are set
- Review backend logs

**"Render keeps spinning down"**
- Render free tier goes idle after 15 min
- Use a free monitoring service like [UptimeRobot](https://uptimerobot.com)
- Set ping URL to `https://your-backend/api/health` every 10 minutes

**"Supabase authentication failed"**
- Double-check credentials in production `.env`
- Verify bucket exists in your project
- Check that Storage is enabled in your Supabase project Settings

**"Upload works but 3D model never appears"**
- Check backend logs for reconstruction errors
- Verify quality stage completed: Check artifacts list in Viewer
- Try with mock_v1 first to isolate issue

---

## Scaling to Production

When you have users:

1. **Migrate database**: SQLite → PostgreSQL (Supabase)
   - Contact Supabase support for assistance
   
2. **Add job queue**: SQLite → Redis
   - Process reconstructions asynchronously
   - Use Render Redis add-on or self-hosted

3. **Use CDN**: CloudFlare for static assets
   - Improves load times globally

4. **Monitor metrics**: Sentry for errors, Datadog for performance

5. **Set rate limits**: Prevent abuse

6. **Implement authentication**: JWT tokens for user accounts

7. **Add payments**: Stripe integration for premium features

---

## Support

- 📖 Docs: [docs/DOCKER_DEPLOYMENT.md](../docs/DOCKER_DEPLOYMENT.md)
- 🐛 Issues: [GitHub Issues](https://github.com/mertmensah/olympus/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/mertmensah/olympus/discussions)

---

**Need help?** Create an issue with your deployment setup and error logs.
