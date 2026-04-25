from __future__ import annotations

from app.services.reconstruct_adapters.base import ReconstructAdapter
from app.services.reconstruct_adapters.mock_v1 import MockReconstructAdapterV1
from app.services.reconstruct_adapters.hf_api_v1 import HFAPIAdapterV1


def get_reconstruct_adapter(name: str) -> ReconstructAdapter:
    normalized = (name or "").strip().lower()

    if normalized in {"mock", "mock_v1", "default"}:
        return MockReconstructAdapterV1()
    
    if normalized in {"hf_api", "hf_api_v1"}:
        return HFAPIAdapterV1()

    raise ValueError(f"Unknown reconstruct adapter: {name}")
