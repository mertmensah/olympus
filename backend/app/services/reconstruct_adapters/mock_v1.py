from __future__ import annotations

import io
from datetime import datetime, timezone

import numpy as np
import trimesh

from app.services.reconstruct_adapters.base import (
    ReconstructAdapter,
    ReconstructAdapterInput,
    ReconstructAdapterOutput,
)


class MockReconstructAdapterV1(ReconstructAdapter):
    name = "mock_v1"
    version = "1.0.0"

    def run(self, model_input: ReconstructAdapterInput) -> ReconstructAdapterOutput:
        """Generate a procedural 3D head mesh scaled by quality score."""
        
        # Generate mesh based on quality score
        mesh = self._generate_head_mesh(
            quality_score=model_input.quality_score,
            height_cm=model_input.profile.get("height_cm", 175),
        )
        
        # Export to GLB
        output_asset_key = f"{model_input.job_id}/outputs/reconstruction.glb"
        glb_bytes = self._mesh_to_glb(mesh)

        return ReconstructAdapterOutput(
            output_asset_key=output_asset_key,
            content_type="model/gltf-binary",
            payload_bytes=glb_bytes,
            adapter_name=self.name,
            adapter_version=self.version,
            metadata={
                "vertex_count": len(mesh.vertices),
                "face_count": len(mesh.faces),
                "selected_asset_count": len(model_input.selected_assets),
                "quality_score": model_input.quality_score,
            },
        )

    def _generate_head_mesh(self, quality_score: float, height_cm: float) -> trimesh.Trimesh:
        """Generate a procedural head/bust mesh."""
        # Scale based on quality score (0.5 to 1.5x)
        scale = 0.5 + quality_score
        
        # Create sphere base (head shape)
        sphere = trimesh.creation.icosphere(subdivisions=4)
        sphere.apply_scale([scale, scale * 1.1, scale])  # Slightly elongated
        
        # Create cylinder (neck)
        neck = trimesh.creation.cylinder(
            radius=scale * 0.4,
            height=scale * 0.8,
        )
        neck.apply_translation([0, 0, -scale * 0.9])
        
        # Create box (shoulders/bust)
        bust = trimesh.creation.box(
            extents=[scale * 2.0, scale * 1.5, scale * 0.6]
        )
        bust.apply_translation([0, 0, -scale * 1.6])
        
        # Combine meshes
        combined = trimesh.util.concatenate([sphere, neck, bust])
        
        # Scale by height (normalize to ~175cm)
        height_scale = height_cm / 175.0
        combined.apply_scale(height_scale)
        
        return combined

    def _mesh_to_glb(self, mesh: trimesh.Trimesh) -> bytes:
        """Convert trimesh to GLB binary format."""
        glb_buffer = io.BytesIO()
        mesh.export(file_obj=glb_buffer, file_type="glb")
        return glb_buffer.getvalue()
