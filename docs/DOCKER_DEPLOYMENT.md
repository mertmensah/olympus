# Olympus Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- Supabase project with S3 bucket created
- (Optional) Hugging Face account for remote inference

### Local Development

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure environment variables** in `.env`:
   ```bash
   SUPABASE_URL=your-project-url
   SUPABASE_SECRET_KEY=your-secret-key
   OLYMPUS_RECONSTRUCT_ADAPTER=mock_v1  # Use mock for development
   ```

3. **Start containers**:
   ```bash
   docker-compose up
   ```

   Backend will be available at: http://localhost:8000  
   Frontend will be available at: http://localhost:5173

4. **Test health**:
   ```bash
   curl http://localhost:8000/api/health
   ```

### Production Deployment

#### Build Docker Image

```bash
docker build -t olympus-backend:latest .
```

#### Run with Environment

```bash
docker run \
  -p 8000:8000 \
  -e SUPABASE_URL="your-url" \
  -e SUPABASE_SECRET_KEY="your-key" \
  -e OLYMPUS_RECONSTRUCT_ADAPTER="mock_v1" \
  -v olympus-data:/app/data \
  olympus-backend:latest
```

#### Using Docker Compose (Production)

1. Create `.env.production`:
   ```bash
   SUPABASE_URL=https://your-production-url.supabase.co
   SUPABASE_SECRET_KEY=your-production-secret-key
   OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1  # Use real inference
   OLYMPUS_HF_API_URL=https://api-inference.huggingface.co/models/your-model
   OLYMPUS_HF_API_TOKEN=hf_your_production_token
   ```

2. Start with production config:
   ```bash
   docker-compose -f docker-compose.yml \
     --env-file .env.production \
     up -d
   ```

### Environment Variables Reference

#### Required
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SECRET_KEY`: Service role key from Supabase

#### Optional (Development)
- `OLYMPUS_RECONSTRUCT_ADAPTER`: `mock_v1` (default, for testing)
- `OLYMPUS_UPLOAD_TOKEN_SECRET`: Secret for upload tokens (default: dev-secret-change-me)
- `OLYMPUS_API_BASE_URL`: Backend base URL (default: http://localhost:8000)

#### Optional (Remote Inference)
- `OLYMPUS_RECONSTRUCT_ADAPTER`: Set to `hf_api_v1`
- `OLYMPUS_HF_API_URL`: Hugging Face endpoint URL
- `OLYMPUS_HF_API_TOKEN`: Hugging Face API token
- `OLYMPUS_HF_API_TIMEOUT`: Request timeout in seconds (default: 30)

### Adapter Strategies

#### Development (mock_v1)
- No external dependencies
- Instant responses
- Procedurally generated mesh
- Best for testing UI/pipeline

```bash
OLYMPUS_RECONSTRUCT_ADAPTER=mock_v1
```

#### Production (hf_api_v1)
- Calls remote inference endpoint
- Real 3D reconstruction
- Requires valid API credentials
- Suitable for production workloads

```bash
OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1
OLYMPUS_HF_API_URL=https://api-inference.huggingface.co/models/stabilityai/stable-fast-3d
OLYMPUS_HF_API_TOKEN=hf_xxxxxxxxxxxx
```

### Container Health Checks

The backend container includes a health check endpoint:

```bash
curl http://localhost:8000/api/health
# Response: {"status": "ok"}
```

Docker will automatically mark the container as unhealthy if health checks fail.

### Data Persistence

- Backend SQLite database: `/app/data/olympus.db`
- Mount as volume: `-v olympus-data:/app/data`
- Persists across container restarts

### Troubleshooting

#### Backend failing to start
```bash
docker-compose logs backend
```

#### Check environment variables
```bash
docker-compose exec backend env | grep OLYMPUS
```

#### Database errors
```bash
# Reset database (loses all data)
docker volume rm olympus_backed_data
docker-compose down && docker-compose up
```

#### Frontend can't reach backend
- Ensure backend is running: `curl http://localhost:8000/api/health`
- Check network: `docker network ls`
- Verify CORS settings in backend

### Scaling

For production, consider:

1. **Load balancing**: Place multiple backend instances behind Nginx
2. **Database**: Migrate from SQLite to PostgreSQL (with Supabase)
3. **Queue system**: Use Redis for job processing
4. **Monitoring**: Add Prometheus/Grafana for metrics

Example with Nginx:

```yaml
nginx:
  image: nginx:latest
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
  depends_on:
    - backend
```

### Security Considerations

1. **Change upload token secret** in production:
   ```bash
   OLYMPUS_UPLOAD_TOKEN_SECRET=$(openssl rand -base64 32)
   ```

2. **Use environment-specific secrets**:
   - Never commit `.env` to git
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault, etc.)

3. **Enable HTTPS** in production:
   - Use reverse proxy with SSL termination (Nginx, Traefik)
   - Set OLYMPUS_API_BASE_URL to https://...

4. **Restrict Supabase bucket** access:
   - Use RLS policies
   - Implement per-user isolation if multi-tenant

### Monitoring & Logging

View logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

Advanced logging:
```bash
# Save logs to file
docker-compose logs backend > backend.log
```

### Updating

1. Pull latest code:
   ```bash
   git pull origin main
   ```

2. Rebuild image:
   ```bash
   docker-compose build --no-cache
   ```

3. Restart services:
   ```bash
   docker-compose up -d
   ```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Supabase Documentation](https://supabase.com/docs)
- [Hugging Face Models](https://huggingface.co/models)
