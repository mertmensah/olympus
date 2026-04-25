"""
Model selection strategy for routing reconstruction requests to different adapters.

Supports:
- Quality-based routing (use fast model for low quality, better model for high quality)
- Fallback chains (try primary, fall back to secondary on failure)
- A/B testing (randomly select between models for experimentation)
"""

import os
from enum import Enum
from typing import Literal
import random

from app.services.reconstruct_adapters.base import ReconstructAdapter
from app.services.reconstruct_adapters.registry import get_reconstruct_adapter


class SelectionStrategy(Enum):
    """Available model selection strategies."""
    FIXED = "fixed"  # Always use one model
    QUALITY_BASED = "quality_based"  # Choose model based on quality score
    FALLBACK = "fallback"  # Try primary, fall back to secondary on error
    AB_TEST = "ab_test"  # Random selection for A/B testing


class ModelSelector:
    """Intelligently select reconstruction adapters based on input characteristics."""

    def __init__(self):
        self.strategy = os.getenv("OLYMPUS_MODEL_SELECTION_STRATEGY", "fixed").lower()
        self.primary_adapter = os.getenv("OLYMPUS_PRIMARY_ADAPTER", "mock_v1")
        self.secondary_adapter = os.getenv("OLYMPUS_SECONDARY_ADAPTER", "mock_v1")
        self.quality_threshold = float(os.getenv("OLYMPUS_QUALITY_THRESHOLD", "0.7"))
        self.high_quality_adapter = os.getenv("OLYMPUS_HIGH_QUALITY_ADAPTER", "hf_api_v1")
        self.low_quality_adapter = os.getenv("OLYMPUS_LOW_QUALITY_ADAPTER", "mock_v1")
        self.ab_split = float(os.getenv("OLYMPUS_AB_SPLIT", "0.5"))  # % for primary

    def select_adapter(
        self,
        quality_score: float = 0.5,
        asset_count: int = 1,
    ) -> tuple[ReconstructAdapter, str]:
        """
        Select appropriate adapter based on input characteristics.

        Args:
            quality_score: Normalized quality score (0.0 to 1.0)
            asset_count: Number of input assets

        Returns:
            Tuple of (adapter_instance, adapter_name)
        """
        if self.strategy == SelectionStrategy.QUALITY_BASED.value:
            return self._quality_based_selection(quality_score, asset_count)
        elif self.strategy == SelectionStrategy.FALLBACK.value:
            # Return primary with metadata indicating fallback is configured
            adapter = get_reconstruct_adapter(self.primary_adapter)
            return adapter, self.primary_adapter
        elif self.strategy == SelectionStrategy.AB_TEST.value:
            return self._ab_test_selection()
        else:  # FIXED or default
            adapter = get_reconstruct_adapter(self.primary_adapter)
            return adapter, self.primary_adapter

    def _quality_based_selection(
        self, quality_score: float, asset_count: int
    ) -> tuple[ReconstructAdapter, str]:
        """
        Select model based on input quality metrics.

        Strategy:
        - High quality (>threshold) + multiple assets -> premium adapter (hf_api_v1)
        - Low quality (<threshold) or single asset -> fast adapter (mock_v1)
        """
        # Adjust threshold based on asset count
        adjusted_threshold = self.quality_threshold
        if asset_count < 3:
            adjusted_threshold += 0.1  # Less confidence with fewer assets
        if asset_count > 8:
            adjusted_threshold -= 0.05  # More confidence with many assets

        if quality_score >= adjusted_threshold and asset_count >= 3:
            adapter_name = self.high_quality_adapter
        else:
            adapter_name = self.low_quality_adapter

        adapter = get_reconstruct_adapter(adapter_name)
        return adapter, adapter_name

    def _ab_test_selection(self) -> tuple[ReconstructAdapter, str]:
        """Randomly select between primary and secondary for A/B testing."""
        if random.random() < self.ab_split:
            adapter_name = self.primary_adapter
        else:
            adapter_name = self.secondary_adapter

        adapter = get_reconstruct_adapter(adapter_name)
        return adapter, adapter_name

    def get_fallback_chain(self) -> list[str]:
        """Get chain of adapters to try in order for fallback strategy."""
        return [self.primary_adapter, self.secondary_adapter]

    def get_selection_metadata(
        self, quality_score: float, asset_count: int
    ) -> dict:
        """Get metadata about the selection decision for logging/analytics."""
        _, selected_adapter = self.select_adapter(quality_score, asset_count)

        return {
            "strategy": self.strategy,
            "selected_adapter": selected_adapter,
            "quality_score": quality_score,
            "asset_count": asset_count,
            "quality_threshold": self.quality_threshold,
            "primary_adapter": self.primary_adapter,
            "secondary_adapter": self.secondary_adapter,
        }


# Singleton instance
_selector = None


def get_model_selector() -> ModelSelector:
    """Get or create the global model selector instance."""
    global _selector
    if _selector is None:
        _selector = ModelSelector()
    return _selector
