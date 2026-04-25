# HF API Adapter Guide

## Overview

The `hf_api_v1` adapter enables the Olympus platform to call remote inference endpoints for 3D reconstruction. This supports services like Hugging Face Inference API, OpenAI, or any custom REST API that accepts JSON payloads and returns reconstruction data.

## Quick Start

### 1. Set Environment Variables

```bash
export OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1
export OLYMPUS_HF_API_URL=https://api-inference.huggingface.co/models/your-model-id
export OLYMPUS_HF_API_TOKEN=your-hf-token-here
export OLYMPUS_HF_API_TIMEOUT=30  # Optional, default: 30 seconds
```

### 2. Start Backend with HF Adapter

```bash
cd backend
python -m uvicorn app.main:app --reload --app-dir .
```

The adapter will now use `hf_api_v1` for all reconstruction requests.

### 3. Test End-to-End

Upload media via the frontend or API—the pipeline will:
1. Ingest assets
2. Run quality checks
3. Call HF API for reconstruction
4. Store output and metrics
5. Complete delivery

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLYMPUS_RECONSTRUCT_ADAPTER` | No | `mock_v1` | Set to `hf_api_v1` to enable remote API calls |
| `OLYMPUS_HF_API_URL` | Yes* | `` | Remote inference endpoint URL |
| `OLYMPUS_HF_API_TOKEN` | Yes* | `` | Bearer token for authentication |
| `OLYMPUS_HF_API_TIMEOUT` | No | `30` | Request timeout in seconds |

*Required only when `OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1`

## Request Format

The adapter sends a JSON POST request to your API endpoint:

```json
{
  "job_id": "90f59a77-95f2-4154-9402-1aaf9677809e",
  "selected_assets": ["asset1.jpg", "asset2.jpg"],
  "quality_score": 0.85,
  "profile": {
    "age": 25,
    "height_cm": 175
  }
}
```

## Response Handling

The adapter expects any JSON response and will embed it in the artifact. Examples:

### Success Response
```json
{
  "status": "success",
  "geometry": {...glb_or_mesh_data...},
  "vertices": 45000,
  "faces": 22500
}
```

### Error Handling
If the API request fails, the adapter gracefully returns an error artifact containing:
- `status: "error"`
- `error: "timeout" | "connection error" | "4xx/5xx response" | message`
- `api_latency_ms: <actual latency>`

The job continues to the postprocess/deliver stages even on reconstruction errors.

## Artifact Output Structure

Successful reconstruction produces an artifact at:
```
GET /api/jobs/{job_id}/artifacts
```

Example artifact:
```json
{
  "stage": "reconstruct",
  "payload": {
    "job_id": "...",
    "adapter": "hf_api_v1",
    "adapter_version": "1.0.0",
    "status": "success",
    "api_response": {...},
    "quality_score": 0.85,
    "selected_assets": [...],
    "api_latency_ms": 2345.67
  },
  "metadata": {
    "api_latency_ms": 2345.67,
    "selected_asset_count": 6,
    "api_status_code": 200
  }
}
```

## Example: Hugging Face Inference API

1. Create a Hugging Face account and get an API token from https://huggingface.co/settings/tokens

2. Find a 3D reconstruction model, or use a text-to-3D model:
   ```bash
   https://api-inference.huggingface.co/models/stabilityai/stable-fast-3d
   ```

3. Set environment variables:
   ```bash
   export OLYMPUS_HF_API_URL=https://api-inference.huggingface.co/models/stabilityai/stable-fast-3d
   export OLYMPUS_HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
   ```

4. Upload an image via the frontend—the pipeline will send it to the model and store the result.

## Fallback Behavior

If the API is unavailable:
1. The adapter returns an error artifact with full details
2. The job continues processing (no blocking)
3. Frontend displays the error for user awareness
4. Job delivery completes with error artifact as the reconstruction output

## Switching Between Adapters

### Use Mock Adapter (Local Testing)
```bash
export OLYMPUS_RECONSTRUCT_ADAPTER=mock_v1
```
No additional setup required; runs instantly with synthetic output.

### Use HF API Adapter (Remote Inference)
```bash
export OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1
export OLYMPUS_HF_API_URL=...
export OLYMPUS_HF_API_TOKEN=...
```
Requires API endpoint and credentials.

### Switching at Runtime
Restart the backend with the desired adapter configuration:
```bash
kill_backend_process
OLYMPUS_RECONSTRUCT_ADAPTER=hf_api_v1 python -m uvicorn app.main:app --app-dir backend
```

## Metrics & Telemetry

Both adapters record:
- **latency_ms**: Time to complete reconstruction (includes network roundtrip for hf_api_v1)
- **peak_memory_kb**: Peak memory usage during processing
- **output_size_bytes**: Size of the output payload
- **content_type**: MIME type of output (application/json)

Access via:
```python
GET /api/jobs/{job_id}/artifacts
# Then filter for stage="reconstruct" and read metadata.latency_ms
```

## Extending: Adding a New Adapter

1. Create `backend/app/services/reconstruct_adapters/my_adapter_v1.py`:
   ```python
   from app.services.reconstruct_adapters.base import ReconstructAdapter, ReconstructAdapterInput, ReconstructAdapterOutput
   
   class MyAdapterV1(ReconstructAdapter):
       name = "my_adapter"
       version = "1.0.0"
       
       def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
           # Your logic here
           return ReconstructAdapterOutput(...)
   ```

2. Register in `backend/app/services/reconstruct_adapters/registry.py`:
   ```python
   if normalized in {"my_adapter", "my_adapter_v1"}:
       return MyAdapterV1()
   ```

3. Set environment variable:
   ```bash
   export OLYMPUS_RECONSTRUCT_ADAPTER=my_adapter_v1
   ```

## Troubleshooting

### Adapter Not Loading
- Check `OLYMPUS_RECONSTRUCT_ADAPTER` matches registered name (see registry.py)
- Verify backend was restarted after changing env vars
- Check backend logs for import errors

### API Timeout
- Increase `OLYMPUS_HF_API_TIMEOUT` (default 30s)
- Check if remote endpoint is responsive
- Verify network connectivity

### 401/403 Authentication Errors
- Verify `OLYMPUS_HF_API_TOKEN` is correct and has necessary permissions
- Check token hasn't expired
- Confirm API URL is correct for your token's organization

### Empty/Invalid Responses
- Check if remote API response format matches expectations
- Review artifact payload in GET /api/jobs/{job_id}/artifacts
- Mock adapter (mock_v1) provides known good reference output
