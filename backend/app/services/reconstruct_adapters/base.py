from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReconstructAdapterInput:
    job_id: str
    selected_assets: list[str]
    quality_score: float
    profile: dict


@dataclass
class ReconstructAdapterOutput:
    output_asset_key: str
    content_type: str
    payload_bytes: bytes
    adapter_name: str
    adapter_version: str
    metadata: dict


class ReconstructAdapter:
    name: str = "base"
    version: str = "0.0.0"

    def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
        raise NotImplementedError("Adapter must implement run()")
