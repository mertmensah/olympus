from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from time import perf_counter

import requests

from app.services.reconstruct_adapters.base import (
    ReconstructAdapter,
    ReconstructAdapterInput,
    ReconstructAdapterOutput,
)


class HFAPIAdapterV1(ReconstructAdapter):
    """
    Adapter for calling remote Hugging Face Inference API or compatible endpoints.
    
    Environment Variables:
    - OLYMPUS_HF_API_URL: Remote endpoint URL (e.g., https://api-inference.huggingface.co/models/...)
    - OLYMPUS_HF_API_TOKEN: Authorization token/key
    - OLYMPUS_HF_API_TIMEOUT: Request timeout in seconds (default: 30)
    """

    name = "hf_api_v1"
    version = "1.0.0"

    def __init__(self):
        self.api_url = os.getenv("OLYMPUS_HF_API_URL", "").strip()
        self.api_token = os.getenv("OLYMPUS_HF_API_TOKEN", "").strip()
        self.timeout = int(os.getenv("OLYMPUS_HF_API_TIMEOUT", "30"))

    def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
        """Call remote inference API and return reconstruction output."""

        if not self.api_url or not self.api_token:
            raise ValueError(
                "HF_API adapter requires OLYMPUS_HF_API_URL and OLYMPUS_HF_API_TOKEN"
            )

        start_ts = perf_counter()
        
        try:
            # Prepare request payload
            request_payload = {
                "job_id": model_input.job_id,
                "selected_assets": model_input.selected_assets,
                "quality_score": model_input.quality_score,
                "profile": model_input.profile,
            }

            # Make API call with Bearer token
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            
            response = requests.post(
                self.api_url,
                json=request_payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Parse response
            api_response = response.json()
            
            latency_ms = (perf_counter() - start_ts) * 1000.0

            # Build output payload with reconstruction data
            output_asset_key = f"{model_input.job_id}/outputs/reconstruction_hf.json"
            
            payload = {
                "job_id": model_input.job_id,
                "adapter": self.name,
                "adapter_version": self.version,
                "status": "success",
                "api_response": api_response,
                "profile": model_input.profile,
                "quality_score": model_input.quality_score,
                "selected_assets": model_input.selected_assets,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "api_latency_ms": latency_ms,
            }

            return ReconstructAdapterOutput(
                output_asset_key=output_asset_key,
                content_type="application/json",
                payload_bytes=json.dumps(payload, indent=2).encode("utf-8"),
                adapter_name=self.name,
                adapter_version=self.version,
                metadata={
                    "api_latency_ms": latency_ms,
                    "selected_asset_count": len(model_input.selected_assets),
                    "api_status_code": response.status_code,
                },
            )

        except requests.exceptions.Timeout:
            latency_ms = (perf_counter() - start_ts) * 1000.0
            error_payload = {
                "job_id": model_input.job_id,
                "adapter": self.name,
                "adapter_version": self.version,
                "status": "error",
                "error": "API request timeout",
                "error_type": "timeout",
                "api_url": self.api_url,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "api_latency_ms": latency_ms,
            }
            return ReconstructAdapterOutput(
                output_asset_key=f"{model_input.job_id}/outputs/reconstruction_hf_error.json",
                content_type="application/json",
                payload_bytes=json.dumps(error_payload, indent=2).encode("utf-8"),
                adapter_name=self.name,
                adapter_version=self.version,
                metadata={
                    "error": "timeout",
                    "api_latency_ms": latency_ms,
                },
            )

        except requests.exceptions.RequestException as e:
            latency_ms = (perf_counter() - start_ts) * 1000.0
            error_payload = {
                "job_id": model_input.job_id,
                "adapter": self.name,
                "adapter_version": self.version,
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "api_url": self.api_url,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "api_latency_ms": latency_ms,
            }
            return ReconstructAdapterOutput(
                output_asset_key=f"{model_input.job_id}/outputs/reconstruction_hf_error.json",
                content_type="application/json",
                payload_bytes=json.dumps(error_payload, indent=2).encode("utf-8"),
                adapter_name=self.name,
                adapter_version=self.version,
                metadata={
                    "error": str(type(e).__name__),
                    "api_latency_ms": latency_ms,
                },
            )

        except Exception as e:
            latency_ms = (perf_counter() - start_ts) * 1000.0
            error_payload = {
                "job_id": model_input.job_id,
                "adapter": self.name,
                "adapter_version": self.version,
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "error_type": type(e).__name__,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "api_latency_ms": latency_ms,
            }
            return ReconstructAdapterOutput(
                output_asset_key=f"{model_input.job_id}/outputs/reconstruction_hf_error.json",
                content_type="application/json",
                payload_bytes=json.dumps(error_payload, indent=2).encode("utf-8"),
                adapter_name=self.name,
                adapter_version=self.version,
                metadata={
                    "error": str(type(e).__name__),
                    "api_latency_ms": latency_ms,
                },
            )
