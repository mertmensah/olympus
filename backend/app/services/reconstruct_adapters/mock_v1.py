from __future__ import annotations

import json
from datetime import datetime, timezone

from app.services.reconstruct_adapters.base import (
    ReconstructAdapter,
    ReconstructAdapterInput,
    ReconstructAdapterOutput,
)


class MockReconstructAdapterV1(ReconstructAdapter):
    name = "mock_v1"
    version = "1.0.0"

    def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
        estimated_vertices = max(12000, int(10000 + model_input.quality_score * 80))
        output_asset_key = f"{model_input.job_id}/outputs/reconstruction.json"

        payload = {
            "job_id": model_input.job_id,
            "adapter": self.name,
            "adapter_version": self.version,
            "estimated_vertices": estimated_vertices,
            "selected_assets": model_input.selected_assets,
            "profile": model_input.profile,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return ReconstructAdapterOutput(
            output_asset_key=output_asset_key,
            content_type="application/json",
            payload_bytes=json.dumps(payload, indent=2).encode("utf-8"),
            adapter_name=self.name,
            adapter_version=self.version,
            metadata={
                "estimated_vertices": estimated_vertices,
                "selected_asset_count": len(model_input.selected_assets),
            },
        )
